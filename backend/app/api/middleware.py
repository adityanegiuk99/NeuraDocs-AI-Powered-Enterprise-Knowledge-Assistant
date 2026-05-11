"""
API middleware stack for production hardening.
Includes: rate limiting, request ID tracking, and request logging.
"""

import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Rate Limiting Middleware
# ═══════════════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter.
    Limits requests per client IP within a configurable time window.

    For production, replace with Redis-backed rate limiting
    (e.g., fastapi-limiter or custom Redis solution).
    """

    def __init__(
        self,
        app: FastAPI,
        max_requests: int = 60,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._request_counts: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For for proxied requests."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client has exceeded the rate limit."""
        now = time.time()
        window_start = now - self.window_seconds

        # Remove expired timestamps
        self._request_counts[client_ip] = [
            ts for ts in self._request_counts[client_ip]
            if ts > window_start
        ]

        # Check limit
        if len(self._request_counts[client_ip]) >= self.max_requests:
            return True

        # Record this request
        self._request_counts[client_ip].append(now)
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ("/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        if self._is_rate_limited(client_ip):
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        response = await call_next(request)

        # Add rate limit headers
        remaining = self.max_requests - len(self._request_counts.get(client_ip, []))
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Window"] = f"{self.window_seconds}s"

        return response


# ═══════════════════════════════════════════════════════════════════
#  Request ID Middleware
# ═══════════════════════════════════════════════════════════════════

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique request ID to every incoming request.
    The ID is returned in the X-Request-ID response header
    and can be used for distributed tracing and log correlation.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


# ═══════════════════════════════════════════════════════════════════
#  Request Logging Middleware
# ═══════════════════════════════════════════════════════════════════

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming request with method, path, status, and latency.
    Provides visibility into API usage patterns and performance.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()

        # Skip logging for health/docs endpoints
        if request.url.path in ("/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        response = await call_next(request)

        latency_ms = round((time.time() - start) * 1000, 1)
        request_id = getattr(request.state, "request_id", "unknown")

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=latency_ms,
            request_id=request_id,
            client=request.client.host if request.client else "unknown",
        )

        return response


# ═══════════════════════════════════════════════════════════════════
#  Middleware Registration
# ═══════════════════════════════════════════════════════════════════

def register_middleware(app: FastAPI, debug: bool = True):
    """
    Register all middleware in the correct order.
    Order matters: outermost middleware runs first.

    Stack (bottom-up execution):
    1. RequestIDMiddleware — assigns request ID
    2. RequestLoggingMiddleware — logs request details
    3. RateLimitMiddleware — enforces rate limits
    """
    # Rate limiter: more permissive in development
    rate_limit = 200 if debug else 60

    app.add_middleware(RateLimitMiddleware, max_requests=rate_limit, window_seconds=60)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

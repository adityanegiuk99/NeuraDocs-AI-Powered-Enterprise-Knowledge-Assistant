"""
FastAPI application entry point.
Configures middleware, lifespan events, and mounts all routes.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.db.session import init_db, close_db
from app.utils.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Runs startup logic before yield, cleanup logic after.
    """
    # ── Startup ──
    setup_logging(debug=settings.debug)
    logger = get_logger("startup")
    logger.info("starting_application", app_name=settings.app_name, env=settings.app_env)

    # Ensure data directories exist
    settings.ensure_directories()

    # Initialize database tables
    await init_db()
    logger.info("database_initialized")

    # TODO: Load FAISS index and embedding model into memory here
    # This ensures they're loaded once at startup, not per-request.

    yield  # ── Application runs here ──

    # ── Shutdown ──
    await close_db()
    logger.info("application_shutdown")


app = FastAPI(
    title="AI Knowledge Assistant API",
    description="Production-grade RAG-powered internal knowledge assistant",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API Routes ──
app.include_router(api_router)


# ── Root Endpoint ──
@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
    }

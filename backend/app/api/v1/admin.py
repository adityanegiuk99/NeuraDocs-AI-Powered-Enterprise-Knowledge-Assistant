"""
Admin API routes: user management, analytics, health check.
"""

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import allow_admin, get_current_user
from app.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.query_log import QueryLog
from app.models.user import User
from app.schemas.admin import HealthResponse, QueryAnalytics, QueryLogResponse
from app.schemas.auth import UserResponse, UserUpdate
from app.utils.logging import get_logger

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = get_logger(__name__)

# Track app start time for uptime
_app_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    System health check. Returns status of all components.
    Public endpoint (for load balancer health checks).
    """
    components = {}

    # Check database
    try:
        await db.execute(select(func.count()).select_from(User))
        components["database"] = "ok"
    except Exception as e:
        components["database"] = f"error: {str(e)}"

    # Check vector store
    from pathlib import Path
    faiss_path = Path(settings.faiss_index_path)
    components["vector_store"] = "ok" if faiss_path.exists() else "not_initialized"

    # Embedding model status
    components["embedding_model"] = "ok"  # Will be checked when model is loaded

    # LLM status
    components["llm_service"] = "configured" if settings.openai_api_key else "not_configured"

    # Aggregate status
    errors = [k for k, v in components.items() if "error" in str(v)]
    overall = "unhealthy" if errors else "healthy"

    # Get counts
    doc_count_result = await db.execute(select(func.count()).select_from(Document))
    total_docs = doc_count_result.scalar() or 0

    # Total chunks approximation
    chunk_result = await db.execute(
        select(func.sum(Document.chunk_count)).select_from(Document)
    )
    total_chunks = chunk_result.scalar() or 0

    return HealthResponse(
        status=overall,
        components=components,
        uptime_seconds=round(time.time() - _app_start_time, 1),
        version="1.0.0",
        total_documents=total_docs,
        total_chunks=total_chunks,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Admin only."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    data: UserUpdate,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role or status. Admin only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id and data.role and data.role != "admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot remove your own admin role",
        )

    if data.role is not None:
        user.role = data.role
    if data.username is not None:
        user.username = data.username
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.flush()
    await db.refresh(user)
    logger.info("user_updated", target_user_id=user_id, by_user_id=current_user.id)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user. Admin only."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    logger.info("user_deleted", target_user_id=user_id, by_user_id=current_user.id)


@router.get("/analytics/queries", response_model=QueryAnalytics)
async def get_query_analytics(
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get query analytics overview. Admin only."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Total queries
    total_result = await db.execute(select(func.count()).select_from(QueryLog))
    total_queries = total_result.scalar() or 0

    if total_queries == 0:
        return QueryAnalytics(
            total_queries=0, avg_latency_ms=0, p95_latency_ms=0,
            success_rate=1.0, avg_confidence=0, queries_today=0,
            queries_this_week=0,
        )

    # Average latency
    avg_lat_result = await db.execute(
        select(func.avg(QueryLog.total_latency_ms)).select_from(QueryLog)
    )
    avg_latency = avg_lat_result.scalar() or 0

    # Success rate
    success_result = await db.execute(
        select(func.count()).select_from(QueryLog).where(QueryLog.status == "success")
    )
    success_count = success_result.scalar() or 0

    # Average confidence
    avg_conf_result = await db.execute(
        select(func.avg(QueryLog.confidence_score)).select_from(QueryLog)
    )

    # Average feedback
    avg_fb_result = await db.execute(
        select(func.avg(QueryLog.user_feedback))
        .select_from(QueryLog)
        .where(QueryLog.user_feedback.isnot(None))
    )

    # Today's queries
    today_result = await db.execute(
        select(func.count())
        .select_from(QueryLog)
        .where(QueryLog.created_at >= today_start)
    )

    # This week's queries
    week_result = await db.execute(
        select(func.count())
        .select_from(QueryLog)
        .where(QueryLog.created_at >= week_start)
    )

    return QueryAnalytics(
        total_queries=total_queries,
        avg_latency_ms=round(avg_latency, 1),
        p95_latency_ms=0,  # Would need percentile calculation
        success_rate=round(success_count / total_queries, 3) if total_queries else 1.0,
        avg_confidence=round(avg_conf_result.scalar() or 0, 3),
        avg_feedback_score=round(avg_fb_result.scalar() or 0, 2) if avg_fb_result.scalar() else None,
        queries_today=today_result.scalar() or 0,
        queries_this_week=week_result.scalar() or 0,
    )


@router.get("/analytics/logs", response_model=list[QueryLogResponse])
async def get_query_logs(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get query logs. Admin only."""
    query = select(QueryLog).order_by(QueryLog.created_at.desc())
    if status_filter:
        query = query.where(QueryLog.status == status_filter)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()

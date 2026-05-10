"""
Chat API routes: query, conversations, history.
"""

import json
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.query_log import QueryLog
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    FeedbackRequest,
    MessageResponse,
    QueryRequest,
    QueryResponse,
    SourceChunk,
)
from app.utils.logging import get_logger

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = get_logger(__name__)


@router.post("/query", response_model=QueryResponse)
async def query(
    data: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a query to the RAG pipeline.
    Returns an AI-generated answer with source citations.
    """
    start_time = time.time()

    # Get or create conversation
    if data.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == data.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            user_id=current_user.id,
            title=data.query[:100],  # Use first 100 chars of query as title
        )
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)

    # ===== RAG Pipeline =====
    # These will be replaced with real implementations in Phase 3

    # Step 1: Get conversation history for context
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(6)
    )
    recent_messages = list(reversed(history_result.scalars().all()))

    # Step 2: Query rewriting (placeholder)
    rewritten_query = data.query

    # Step 3: Retrieval (placeholder — will integrate FAISS)
    embed_start = time.time()
    embed_ms = (time.time() - embed_start) * 1000

    retrieval_start = time.time()
    # Placeholder: no retrieval yet
    retrieved_sources = []
    retrieval_ms = (time.time() - retrieval_start) * 1000

    rerank_start = time.time()
    rerank_ms = (time.time() - rerank_start) * 1000

    # Step 4: Generation (placeholder)
    gen_start = time.time()
    answer = (
        "I'm the Knowledge Assistant. The RAG pipeline is being set up. "
        "Once documents are ingested and the retrieval system is configured, "
        "I'll be able to answer questions based on your organization's knowledge base."
    )
    confidence = 0.0
    gen_ms = (time.time() - gen_start) * 1000

    total_ms = (time.time() - start_time) * 1000

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.query,
    )
    db.add(user_msg)

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=json.dumps([s.model_dump() for s in retrieved_sources]),
        confidence=confidence,
        latency_ms=total_ms,
    )
    db.add(assistant_msg)

    # Update conversation
    conversation.message_count += 2

    # Log the query
    query_log = QueryLog(
        user_id=current_user.id,
        conversation_id=conversation.id,
        query_text=data.query,
        rewritten_query=rewritten_query,
        generated_answer=answer,
        retrieved_chunk_ids=json.dumps([]),
        retrieval_scores=json.dumps([]),
        top_score=0.0,
        chunks_retrieved=0,
        model_used="placeholder",
        confidence_score=confidence,
        embedding_latency_ms=embed_ms,
        retrieval_latency_ms=retrieval_ms,
        reranking_latency_ms=rerank_ms,
        generation_latency_ms=gen_ms,
        total_latency_ms=total_ms,
        status="success",
    )
    db.add(query_log)
    await db.flush()

    logger.info(
        "query_processed",
        query_id=query_log.id,
        user_id=current_user.id,
        latency_ms=round(total_ms, 1),
        confidence=confidence,
    )

    return QueryResponse(
        answer=answer,
        sources=retrieved_sources,
        conversation_id=conversation.id,
        confidence=confidence,
        latency_ms=round(total_ms, 1),
    )


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    conversation = Conversation(
        user_id=current_user.id,
        title=data.title,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/history/{conversation_id}", response_model=list[MessageResponse])
async def get_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get message history for a conversation."""
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()


@router.post("/feedback")
async def submit_feedback(
    data: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback (1-5 rating) on a query response."""
    result = await db.execute(
        select(QueryLog).where(
            QueryLog.id == data.query_log_id,
            QueryLog.user_id == current_user.id,
        )
    )
    query_log = result.scalar_one_or_none()
    if not query_log:
        raise HTTPException(status_code=404, detail="Query log not found")

    query_log.user_feedback = data.rating
    query_log.feedback_text = data.feedback_text
    await db.flush()

    logger.info("feedback_submitted", query_log_id=data.query_log_id, rating=data.rating)
    return {"status": "ok", "message": "Feedback recorded"}

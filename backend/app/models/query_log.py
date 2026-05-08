"""
Query log model for analytics and debugging.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_query: Mapped[str] = mapped_column(Text, nullable=True)
    generated_answer: Mapped[str] = mapped_column(Text, nullable=True)

    # Retrieval details
    retrieved_chunk_ids: Mapped[str] = mapped_column(Text, nullable=True)  # JSON list
    retrieval_scores: Mapped[str] = mapped_column(Text, nullable=True)  # JSON list
    top_score: Mapped[float] = mapped_column(Float, nullable=True)
    chunks_retrieved: Mapped[int] = mapped_column(Integer, default=0)

    # Model info
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Latency breakdown (all in milliseconds)
    embedding_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    retrieval_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    reranking_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    generation_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    total_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)

    # Feedback
    user_feedback: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5 rating
    feedback_text: Mapped[str] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, no_results, error
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<QueryLog(id={self.id}, status={self.status})>"

"""
Chat request/response schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MetadataFilter(BaseModel):
    """Filters to scope retrieval by metadata."""
    department: Optional[str] = None
    doc_type: Optional[str] = None
    tags: Optional[list[str]] = None


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    filters: Optional[MetadataFilter] = None


class SourceChunk(BaseModel):
    document_id: str
    document_title: str
    chunk_text: str
    relevance_score: float
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    metadata: dict = {}


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    conversation_id: str
    confidence: float
    latency_ms: float


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationResponse(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: Optional[str] = None
    confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackRequest(BaseModel):
    query_log_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None

"""
Admin and evaluation schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    components: dict
    uptime_seconds: float
    version: str
    total_documents: int
    total_chunks: int


class QueryAnalytics(BaseModel):
    total_queries: int
    avg_latency_ms: float
    p95_latency_ms: float
    success_rate: float
    avg_confidence: float
    avg_feedback_score: Optional[float] = None
    queries_today: int
    queries_this_week: int


class LatencyMetrics(BaseModel):
    period: str
    avg_embedding_ms: float
    avg_retrieval_ms: float
    avg_reranking_ms: float
    avg_generation_ms: float
    avg_total_ms: float
    p95_total_ms: float


class EvalRunRequest(BaseModel):
    benchmark_id: str = "default"
    top_k: int = 5


class EvalResult(BaseModel):
    id: str
    benchmark_id: str
    run_date: datetime
    total_queries: int
    # Retrieval metrics
    avg_precision_at_k: float
    avg_recall_at_k: float
    avg_mrr: float
    # Generation metrics
    avg_faithfulness: float
    avg_relevancy: float
    # Latency
    avg_latency_ms: float
    p95_latency_ms: float
    # Status
    status: str


class QueryLogResponse(BaseModel):
    id: str
    user_id: str
    query_text: str
    generated_answer: Optional[str]
    model_used: Optional[str]
    total_latency_ms: Optional[float]
    confidence_score: Optional[float]
    user_feedback: Optional[int]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

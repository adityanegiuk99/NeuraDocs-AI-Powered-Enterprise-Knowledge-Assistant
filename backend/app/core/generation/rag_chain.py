"""
Full RAG chain orchestrator.
Coordinates: memory → query rewrite → retrieve → generate → log.
This is the top-level service that the chat API calls.
"""

import time
from dataclasses import dataclass
from typing import Optional

from app.core.generation.llm import BaseLLM
from app.core.generation.prompts import (
    SYSTEM_PROMPT,
    build_rag_prompt,
    build_rewrite_prompt,
)
from app.core.retrieval.retriever import Retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""
    answer: str
    sources: list[dict]
    rewritten_query: Optional[str]
    confidence: float
    latency: dict  # per-component timing


class RAGChain:
    """
    End-to-end RAG pipeline.
    
    Flow:
    1. Get conversation history from memory
    2. Rewrite query for standalone search
    3. Retrieve relevant chunks (hybrid search + rerank)
    4. Check retrieval gate (are results relevant enough?)
    5. Build grounded prompt with context
    6. Generate response via LLM
    7. Return response with sources and latency
    """

    def __init__(
        self,
        llm: BaseLLM,
        retriever: Retriever,
    ):
        self.llm = llm
        self.retriever = retriever

    def run(
        self,
        query: str,
        conversation_history: str = "",
        metadata_filter: dict = None,
        top_k: int = 5,
    ) -> RAGResponse:
        """Execute the full RAG pipeline."""
        latency = {}
        total_start = time.time()

        # Step 1: Query rewriting (for conversational context)
        rewritten_query = query
        if conversation_history and conversation_history.strip() != "No previous conversation.":
            try:
                t0 = time.time()
                rewrite_prompt = build_rewrite_prompt(query, conversation_history)
                rewritten_query = self.llm.generate(
                    system_prompt="You are a search query optimizer.",
                    user_prompt=rewrite_prompt,
                    max_tokens=150,
                    temperature=0.0,
                ).strip()
                latency["rewrite_ms"] = round((time.time() - t0) * 1000, 1)
                logger.info("query_rewritten", original=query[:80], rewritten=rewritten_query[:80])
            except Exception as e:
                logger.warning("query_rewrite_failed", error=str(e))
                rewritten_query = query
                latency["rewrite_ms"] = 0
        else:
            latency["rewrite_ms"] = 0

        # Step 2: Retrieve relevant chunks
        t0 = time.time()
        retrieval_result = self.retriever.retrieve(
            query=rewritten_query,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
        latency["retrieval_ms"] = round((time.time() - t0) * 1000, 1)
        latency.update(retrieval_result.latency)

        # Step 3: Check retrieval gate
        if not retrieval_result.passed_gate or not retrieval_result.chunks:
            return RAGResponse(
                answer="I couldn't find relevant information in the knowledge base for your question. "
                       "Please try rephrasing or check with the relevant department.",
                sources=[],
                rewritten_query=rewritten_query,
                confidence=0.0,
                latency={**latency, "generation_ms": 0,
                         "total_ms": round((time.time() - total_start) * 1000, 1)},
            )

        # Step 4: Build RAG prompt
        rag_prompt = build_rag_prompt(
            query=query,
            context_chunks=retrieval_result.chunks,
            conversation_history=conversation_history,
        )

        # Step 5: Generate response
        t0 = time.time()
        answer = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=rag_prompt,
        )
        latency["generation_ms"] = round((time.time() - t0) * 1000, 1)

        # Step 6: Calculate confidence
        # Based on: top retrieval score + number of sources with good scores
        top_score = retrieval_result.chunks[0].get(
            "rerank_score",
            retrieval_result.chunks[0].get("score", 0)
        )
        # Normalize to 0-1 range
        confidence = min(max(float(top_score), 0), 1.0)

        latency["total_ms"] = round((time.time() - total_start) * 1000, 1)

        logger.info(
            "rag_chain_complete",
            sources=len(retrieval_result.chunks),
            confidence=round(confidence, 3),
            total_ms=latency["total_ms"],
        )

        return RAGResponse(
            answer=answer,
            sources=retrieval_result.chunks,
            rewritten_query=rewritten_query if rewritten_query != query else None,
            confidence=confidence,
            latency=latency,
        )

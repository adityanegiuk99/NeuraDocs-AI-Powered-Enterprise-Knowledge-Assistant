"""
Main retriever orchestrator.
Coordinates: embed query → hybrid search → filter → rerank → gate → return.
This is the single entry point for the retrieval subsystem.
"""

import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.config import settings
from app.core.embeddings.base import BaseEmbedding
from app.core.retrieval.hybrid import BM25Search, reciprocal_rank_fusion
from app.core.retrieval.reranker import CrossEncoderReranker
from app.core.retrieval.vector_store import FAISSVectorStore
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """Result from the full retrieval pipeline."""
    chunks: list[dict]
    latency: dict  # embedding_ms, retrieval_ms, reranking_ms
    total_candidates: int
    passed_gate: bool  # Whether results passed relevance threshold


class Retriever:
    """
    Full retrieval pipeline orchestrator.
    
    Pipeline:
    1. Embed query
    2. Dense search (FAISS)
    3. Sparse search (BM25) — optional
    4. Reciprocal Rank Fusion
    5. Metadata filtering
    6. Retrieval gate (similarity threshold)
    7. Cross-encoder reranking
    """

    def __init__(
        self,
        embedding_service: BaseEmbedding,
        vector_store: FAISSVectorStore,
        bm25_search: Optional[BM25Search] = None,
        reranker: Optional[CrossEncoderReranker] = None,
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.bm25_search = bm25_search
        self.reranker = reranker

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        metadata_filter: dict = None,
    ) -> RetrievalResult:
        """
        Run the full retrieval pipeline.
        
        Args:
            query: The search query (already rewritten if needed)
            top_k: Number of final results to return
            metadata_filter: Optional metadata filter (department, doc_type, etc.)
        
        Returns:
            RetrievalResult with ranked chunks and latency metrics
        """
        top_k = top_k or settings.top_k_rerank
        latency = {}

        # Step 1: Embed query
        t0 = time.time()
        query_vector = self.embedding_service.embed_query(query)
        latency["embedding_ms"] = round((time.time() - t0) * 1000, 1)

        # Step 2: Dense search
        t0 = time.time()
        dense_results = self.vector_store.search(
            query_vector,
            top_k=settings.top_k_retrieval,
            metadata_filter=metadata_filter,
        )
        latency["dense_search_ms"] = round((time.time() - t0) * 1000, 1)

        # Step 3: Sparse search (BM25)
        sparse_results = []
        if self.bm25_search:
            t0 = time.time()
            sparse_results = self.bm25_search.search(query, top_k=settings.top_k_retrieval)
            latency["sparse_search_ms"] = round((time.time() - t0) * 1000, 1)

        # Step 4: Fusion
        if sparse_results:
            candidates = reciprocal_rank_fusion(dense_results, sparse_results)
        else:
            candidates = dense_results

        total_candidates = len(candidates)

        # Step 5: Retrieval gate — check if top result passes threshold
        passed_gate = True
        if candidates:
            top_score = candidates[0].get("score", candidates[0].get("rrf_score", 0))
            if top_score < settings.similarity_threshold:
                passed_gate = False
                logger.info(
                    "retrieval_gate_failed",
                    top_score=round(top_score, 4),
                    threshold=settings.similarity_threshold,
                )

        # Step 6: Rerank top candidates
        if self.reranker and candidates and passed_gate:
            t0 = time.time()
            # Rerank more candidates than needed for better precision
            rerank_input = candidates[:min(20, len(candidates))]
            candidates = self.reranker.rerank(query, rerank_input, top_k=top_k)
            latency["reranking_ms"] = round((time.time() - t0) * 1000, 1)
        else:
            candidates = candidates[:top_k]
            latency["reranking_ms"] = 0

        logger.info(
            "retrieval_complete",
            query_preview=query[:80],
            total_candidates=total_candidates,
            returned=len(candidates),
            passed_gate=passed_gate,
        )

        return RetrievalResult(
            chunks=candidates,
            latency=latency,
            total_candidates=total_candidates,
            passed_gate=passed_gate,
        )

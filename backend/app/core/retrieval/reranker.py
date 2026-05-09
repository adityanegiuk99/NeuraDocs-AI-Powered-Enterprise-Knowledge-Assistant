"""
Cross-encoder reranker for precise relevance scoring.
Uses a cross-encoder model that jointly scores (query, document) pairs,
which is far more accurate than bi-encoder similarity but also slower.
This is why we rerank only the top candidates from initial retrieval.
"""

from typing import Optional

import numpy as np

from app.utils.logging import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """
    Reranks retrieved chunks using a cross-encoder model.
    
    Why this matters:
    - Bi-encoders (used in FAISS) embed query and document independently
    - Cross-encoders process query+document TOGETHER, enabling richer interaction
    - This gives much more precise relevance scores, but is too slow for full corpus
    - Solution: Use bi-encoder for recall (top 50), cross-encoder for precision (top 5)
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = None
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        """Lazy-load the cross-encoder model."""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            logger.info("reranker_loaded", model=self.model_name)
        except Exception as e:
            logger.warning("reranker_not_available", error=str(e))
            self.model = None

    def rerank(
        self,
        query: str,
        results: list[dict],
        top_k: int = 5,
        text_key: str = "text",
    ) -> list[dict]:
        """
        Rerank results using cross-encoder scores.
        
        Args:
            query: The user's search query
            results: List of result dicts from initial retrieval
            top_k: Number of results to return after reranking
            text_key: Key in result dict containing the text to score
        
        Returns:
            Top-k results re-sorted by cross-encoder score
        """
        if not results:
            return []

        if not self.model:
            # Fallback: return original ordering
            logger.warning("reranker_fallback_to_original_order")
            return results[:top_k]

        # Create (query, passage) pairs for scoring
        pairs = [(query, r.get(text_key, "")) for r in results]

        # Score all pairs
        scores = self.model.predict(pairs)

        # Attach scores and sort
        for result, score in zip(results, scores):
            result["rerank_score"] = float(score)

        reranked = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)

        logger.info(
            "reranking_complete",
            input_count=len(results),
            output_count=min(top_k, len(reranked)),
            top_score=round(reranked[0]["rerank_score"], 4) if reranked else 0,
        )

        return reranked[:top_k]

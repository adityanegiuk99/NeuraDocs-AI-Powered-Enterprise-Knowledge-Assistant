"""
Hybrid search combining dense (FAISS) and sparse (BM25) retrieval
with Reciprocal Rank Fusion for merging results.
"""

import re
from typing import Optional

import numpy as np
from rank_bm25 import BM25Okapi

from app.utils.logging import get_logger

logger = get_logger(__name__)


class BM25Search:
    """
    BM25 sparse keyword search over document chunks.
    Complements dense vector search by capturing exact keyword matches.
    """

    def __init__(self):
        self.corpus: list[str] = []
        self.metadata: list[dict] = []
        self.bm25: Optional[BM25Okapi] = None

    def build_index(self, texts: list[str], metadata_list: list[dict]):
        """Build BM25 index from texts."""
        self.corpus = texts
        self.metadata = metadata_list
        tokenized = [self._tokenize(text) for text in texts]
        self.bm25 = BM25Okapi(tokenized)
        logger.info("bm25_index_built", documents=len(texts))

    def search(self, query: str, top_k: int = 50) -> list[dict]:
        """Search using BM25 scoring."""
        if not self.bm25 or not self.corpus:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                result = self.metadata[idx].copy()
                result["bm25_score"] = float(scores[idx])
                results.append(result)

        return results

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace + punctuation tokenization."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.split()


def reciprocal_rank_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int = 60,
    dense_weight: float = 0.7,
    sparse_weight: float = 0.3,
) -> list[dict]:
    """
    Merge dense and sparse search results using Reciprocal Rank Fusion.
    
    RRF score = sum(weight / (k + rank)) for each result list.
    
    Args:
        dense_results: Results from vector search (ordered by similarity)
        sparse_results: Results from BM25 search (ordered by BM25 score)
        k: Constant to prevent high-ranked items from dominating (default 60)
        dense_weight: Weight for dense retrieval contribution
        sparse_weight: Weight for sparse retrieval contribution
    
    Returns:
        Merged results sorted by fused score
    """
    fused_scores: dict[str, dict] = {}

    def get_chunk_key(result: dict) -> str:
        """Create a unique key for deduplication."""
        return result.get("chunk_id", result.get("text", "")[:100])

    # Score dense results
    for rank, result in enumerate(dense_results):
        key = get_chunk_key(result)
        if key not in fused_scores:
            fused_scores[key] = result.copy()
            fused_scores[key]["rrf_score"] = 0

        fused_scores[key]["rrf_score"] += dense_weight / (k + rank + 1)
        fused_scores[key]["dense_rank"] = rank + 1

    # Score sparse results
    for rank, result in enumerate(sparse_results):
        key = get_chunk_key(result)
        if key not in fused_scores:
            fused_scores[key] = result.copy()
            fused_scores[key]["rrf_score"] = 0

        fused_scores[key]["rrf_score"] += sparse_weight / (k + rank + 1)
        fused_scores[key]["sparse_rank"] = rank + 1

    # Sort by fused score
    merged = sorted(fused_scores.values(), key=lambda x: x["rrf_score"], reverse=True)

    logger.info(
        "rrf_fusion",
        dense_count=len(dense_results),
        sparse_count=len(sparse_results),
        merged_count=len(merged),
    )

    return merged

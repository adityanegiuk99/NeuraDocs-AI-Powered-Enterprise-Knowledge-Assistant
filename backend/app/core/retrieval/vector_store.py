"""
FAISS vector store wrapper with metadata sidecar.
Handles index persistence, addition, search, and deletion.
"""

import json
import math
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FAISSVectorStore:
    """
    FAISS vector store with JSON metadata sidecar.
    
    Architecture:
    - FAISS stores only vectors (indexed by sequential integer IDs)
    - Metadata (text, document_id, etc.) stored in a JSON sidecar file
    - IDs are mapped: FAISS internal ID → metadata entry
    """

    def __init__(
        self,
        dimension: int = 384,
        index_path: str = None,
        metadata_path: str = None,
    ):
        self.dimension = dimension
        self.index_path = index_path or settings.faiss_index_path
        self.metadata_path = metadata_path or settings.faiss_metadata_path
        self.metadata: list[dict] = []

        # Try to load existing index
        if Path(self.index_path).exists() and Path(self.metadata_path).exists():
            self._load()
        else:
            # Create new index — Inner Product (works as cosine sim with normalized vectors)
            self.index = faiss.IndexFlatIP(dimension)
            logger.info("faiss_index_created", dimension=dimension)

    def add(self, embeddings: np.ndarray, metadata_list: list[dict]):
        """
        Add vectors with associated metadata to the store.
        
        Args:
            embeddings: numpy array of shape (n, dimension)
            metadata_list: list of metadata dicts, one per vector
        """
        if len(embeddings) == 0:
            return

        if len(embeddings) != len(metadata_list):
            raise ValueError(
                f"Mismatch: {len(embeddings)} embeddings vs {len(metadata_list)} metadata entries"
            )

        # Ensure correct dtype and shape
        embeddings = np.array(embeddings, dtype=np.float32)
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        # Normalize vectors for cosine similarity via inner product
        faiss.normalize_L2(embeddings)

        self.index.add(embeddings)
        self.metadata.extend(metadata_list)

        self._save()
        logger.info("vectors_added", count=len(embeddings), total=self.index.ntotal)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 50,
        metadata_filter: dict = None,
    ) -> list[dict]:
        """
        Search for similar vectors.
        
        Returns list of dicts with 'score' and all metadata fields.
        Optionally filters by metadata (department, doc_type, etc.).
        """
        if self.index.ntotal == 0:
            return []

        query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(query_vector)

        # Search more than needed if we'll filter
        search_k = min(top_k * 3, self.index.ntotal) if metadata_filter else top_k

        scores, indices = self.index.search(query_vector, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue

            meta = self.metadata[idx].copy()
            meta["score"] = float(score)
            meta["faiss_id"] = int(idx)

            # Apply metadata filter
            if metadata_filter and not self._matches_filter(meta, metadata_filter):
                continue

            results.append(meta)

            if len(results) >= top_k:
                break

        return results

    def delete_by_document(self, document_id: str):
        """
        Delete all vectors for a given document.
        
        Note: FAISS doesn't support efficient deletion for IndexFlat.
        We rebuild the index without the deleted vectors.
        """
        if self.index.ntotal == 0:
            return

        # Find indices to keep
        keep_indices = []
        new_metadata = []
        for i, meta in enumerate(self.metadata):
            if meta.get("document_id") != document_id:
                keep_indices.append(i)
                new_metadata.append(meta)

        if len(keep_indices) == len(self.metadata):
            return  # Nothing to delete

        # Reconstruct vectors for kept indices
        if keep_indices:
            vectors = np.array([
                self.index.reconstruct(i) for i in keep_indices
            ], dtype=np.float32)

            # Rebuild index
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(vectors)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)

        self.metadata = new_metadata
        self._save()

        removed = len(self.metadata) - len(new_metadata) + len(new_metadata)
        logger.info("vectors_deleted", document_id=document_id, remaining=self.index.ntotal)

    def _matches_filter(self, meta: dict, filters: dict) -> bool:
        """Check if metadata matches all filter criteria."""
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, list):
                # For tags: check if any tag matches
                meta_value = meta.get(key, "")
                if isinstance(meta_value, str):
                    try:
                        meta_tags = json.loads(meta_value)
                    except (json.JSONDecodeError, TypeError):
                        meta_tags = [meta_value]
                else:
                    meta_tags = meta_value or []
                if not any(v in meta_tags for v in value):
                    return False
            else:
                if meta.get(key) != value:
                    return False
        return True

    def _save(self):
        """Persist index and metadata to disk."""
        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, self.index_path)

        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f)

    def _load(self):
        """Load index and metadata from disk."""
        self.index = faiss.read_index(self.index_path)
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)

        logger.info("faiss_index_loaded", vectors=self.index.ntotal)

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal

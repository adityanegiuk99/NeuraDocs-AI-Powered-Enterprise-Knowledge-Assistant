"""
HuggingFace sentence-transformers embedding provider.
Uses all-MiniLM-L6-v2 by default (384 dimensions, fast, good quality).
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.embeddings.base import BaseEmbedding
from app.utils.logging import get_logger

logger = get_logger(__name__)


class HuggingFaceEmbedding(BaseEmbedding):
    """
    Embedding provider using HuggingFace sentence-transformers.
    Model is loaded once and cached in memory.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info("loading_embedding_model", model=model_name)
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info("embedding_model_loaded", model=model_name, dimension=self._dimension)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts."""
        if not texts:
            return np.array([])

        embeddings = self._model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,  # Normalize for cosine similarity
        )
        return np.array(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query."""
        embedding = self._model.encode(
            [query],
            normalize_embeddings=True,
        )
        return np.array(embedding[0], dtype=np.float32)

    @property
    def dimension(self) -> int:
        return self._dimension

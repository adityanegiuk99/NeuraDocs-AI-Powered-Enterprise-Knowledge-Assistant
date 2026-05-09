"""
OpenAI embedding provider.
Uses text-embedding-3-small by default (1536 dimensions).
"""

import numpy as np
from openai import OpenAI

from app.core.embeddings.base import BaseEmbedding
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIEmbedding(BaseEmbedding):
    """
    Embedding provider using OpenAI's embedding API.
    Requires OPENAI_API_KEY to be set.
    """

    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, model_name: str = "text-embedding-3-small"):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = model_name
        self._dimension = self.DIMENSIONS.get(model_name, 1536)
        logger.info("openai_embedding_initialized", model=model_name)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts via OpenAI API."""
        if not texts:
            return np.array([])

        # OpenAI API supports batches up to 2048
        all_embeddings = []
        batch_size = 500

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self._client.embeddings.create(
                input=batch,
                model=self._model,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query via OpenAI API."""
        response = self._client.embeddings.create(
            input=[query],
            model=self._model,
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    @property
    def dimension(self) -> int:
        return self._dimension

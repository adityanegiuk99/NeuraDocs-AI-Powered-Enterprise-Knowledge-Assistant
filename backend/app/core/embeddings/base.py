"""
Abstract base class for embedding providers.
Allows swapping between HuggingFace, OpenAI, etc.
"""

from abc import ABC, abstractmethod

import numpy as np


class BaseEmbedding(ABC):
    """Interface that all embedding providers must implement."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts. Returns array of shape (n, dimension)."""
        ...

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query. Returns array of shape (dimension,)."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...

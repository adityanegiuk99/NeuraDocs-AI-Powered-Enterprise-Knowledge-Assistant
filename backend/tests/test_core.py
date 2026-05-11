"""
Unit tests for core business logic modules.
Tests security utilities, ingestion components, and configuration.
"""

import pytest
from datetime import timedelta

from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Test bcrypt password hashing and verification."""

    def test_hash_and_verify(self):
        """Hashed password should verify correctly."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        """Wrong password should not verify."""
        hashed = hash_password("CorrectPassword123!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_hash_is_unique(self):
        """Same password should produce different hashes (bcrypt salt)."""
        password = "SamePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # bcrypt uses random salt

    def test_hash_is_not_plaintext(self):
        """Hash should not contain the original password."""
        password = "PlainTextCheck!"
        hashed = hash_password(password)
        assert password not in hashed


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_access_token_roundtrip(self):
        """Access token should encode and decode correctly."""
        data = {"sub": "user-123", "role": "engineer"}
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        """Refresh token should encode and decode with type=refresh."""
        data = {"sub": "user-456"}
        token = create_refresh_token(data)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_expired_token_returns_none(self):
        """Expired token should return None on decode."""
        data = {"sub": "user-789"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-10))
        payload = decode_token(token)
        assert payload is None

    def test_invalid_token_returns_none(self):
        """Malformed token should return None."""
        assert decode_token("not.a.valid.token") is None
        assert decode_token("") is None

    def test_token_contains_expiry(self):
        """Token payload should contain 'exp' claim."""
        token = create_access_token({"sub": "user-test"})
        payload = decode_token(token)
        assert "exp" in payload


class TestChunker:
    """Test semantic document chunking logic."""

    def test_import_chunker(self):
        """SmartChunker should be importable."""
        from app.core.ingestion.chunker import SmartChunker
        chunker = SmartChunker()
        assert chunker is not None

    def test_chunker_config(self):
        """Chunker should accept custom configuration."""
        from app.core.ingestion.chunker import SmartChunker
        chunker = SmartChunker(
            max_chunk_tokens=256,
            overlap_tokens=32,
        )
        assert chunker.max_chunk_tokens == 256
        assert chunker.overlap_tokens == 32


class TestParser:
    """Test document parser."""

    def test_import_parser(self):
        """DocumentParser should be importable."""
        from app.core.ingestion.parser import DocumentParser
        parser = DocumentParser()
        assert parser is not None


class TestMetadataExtractor:
    """Test metadata extraction."""

    def test_import_metadata_extractor(self):
        """MetadataExtractor should be importable."""
        from app.core.ingestion.metadata import MetadataExtractor
        extractor = MetadataExtractor()
        assert extractor is not None


class TestEmbeddingBase:
    """Test embedding service base class."""

    def test_import_base_embedding(self):
        """BaseEmbedding should be importable and abstract."""
        from app.core.embeddings.base import BaseEmbedding
        assert BaseEmbedding is not None


class TestVectorStore:
    """Test FAISS vector store."""

    def test_import_vector_store(self):
        """FAISSVectorStore should be importable."""
        from app.core.retrieval.vector_store import FAISSVectorStore
        assert FAISSVectorStore is not None


class TestRetriever:
    """Test retriever orchestrator."""

    def test_import_retriever(self):
        """Retriever should be importable."""
        from app.core.retrieval.retriever import Retriever, RetrievalResult
        assert Retriever is not None
        assert RetrievalResult is not None


class TestRAGChain:
    """Test RAG chain orchestrator."""

    def test_import_rag_chain(self):
        """RAGChain should be importable."""
        from app.core.generation.rag_chain import RAGChain, RAGResponse
        assert RAGChain is not None
        assert RAGResponse is not None


class TestConfiguration:
    """Test application configuration."""

    def test_settings_defaults(self):
        """Settings should have sensible defaults."""
        from app.config import settings
        assert settings.app_name == "knowledge-assistant"
        assert settings.embedding_dimension == 384
        assert settings.top_k_rerank == 5
        assert settings.similarity_threshold == 0.35

    def test_ensure_directories(self):
        """ensure_directories() should not raise."""
        from app.config import settings
        settings.ensure_directories()  # Should not raise

    def test_is_production(self):
        """is_production should reflect app_env."""
        from app.config import settings
        assert settings.is_production is False  # default is development

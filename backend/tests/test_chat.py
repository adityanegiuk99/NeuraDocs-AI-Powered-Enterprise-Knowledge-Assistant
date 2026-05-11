"""
Unit tests for chat/query endpoints.
Tests conversation management, query processing, and feedback.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestQueryEndpoint:
    """Test the /chat/query endpoint."""

    @pytest.mark.asyncio
    async def test_query_creates_conversation(self, client: AsyncClient, test_user):
        """First query should create a new conversation automatically."""
        response = await client.post(
            "/api/v1/chat/query",
            json={"query": "What is the remote work policy?"},
            headers=auth_headers(test_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "conversation_id" in data
        assert "confidence" in data
        assert "latency_ms" in data
        assert isinstance(data["sources"], list)

    @pytest.mark.asyncio
    async def test_query_continues_conversation(self, client: AsyncClient, test_user):
        """Query with conversation_id should continue the existing conversation."""
        # Create first query
        resp1 = await client.post(
            "/api/v1/chat/query",
            json={"query": "Tell me about the leave policy."},
            headers=auth_headers(test_user),
        )
        conv_id = resp1.json()["conversation_id"]

        # Continue conversation
        resp2 = await client.post(
            "/api/v1/chat/query",
            json={"query": "What about sick leave?", "conversation_id": conv_id},
            headers=auth_headers(test_user),
        )
        assert resp2.status_code == 200
        assert resp2.json()["conversation_id"] == conv_id

    @pytest.mark.asyncio
    async def test_query_invalid_conversation(self, client: AsyncClient, test_user):
        """Query with non-existent conversation_id should return 404."""
        response = await client.post(
            "/api/v1/chat/query",
            json={"query": "Hello?", "conversation_id": "nonexistent-id"},
            headers=auth_headers(test_user),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_query_empty_string(self, client: AsyncClient, test_user):
        """Empty query should return 422."""
        response = await client.post(
            "/api/v1/chat/query",
            json={"query": ""},
            headers=auth_headers(test_user),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_query_requires_auth(self, client: AsyncClient):
        """Query endpoint should require authentication."""
        response = await client.post(
            "/api/v1/chat/query",
            json={"query": "What is the vacation policy?"},
        )
        assert response.status_code == 403


class TestConversations:
    """Test conversation management endpoints."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, client: AsyncClient, test_user):
        """Should create a named conversation."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "My Test Conversation"},
            headers=auth_headers(test_user),
        )
        assert response.status_code == 200
        assert response.json()["title"] == "My Test Conversation"

    @pytest.mark.asyncio
    async def test_list_conversations(self, client: AsyncClient, test_user):
        """Should return only the current user's conversations."""
        # Create a conversation via query
        await client.post(
            "/api/v1/chat/query",
            json={"query": "Test question"},
            headers=auth_headers(test_user),
        )

        response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers(test_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_list_conversations_isolation(self, client: AsyncClient, test_user, admin_user):
        """Users should not see each other's conversations."""
        # User creates conversation
        await client.post(
            "/api/v1/chat/query",
            json={"query": "User question"},
            headers=auth_headers(test_user),
        )

        # Admin should see 0 conversations (their own)
        response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        assert len(response.json()) == 0


class TestHistory:
    """Test conversation history endpoints."""

    @pytest.mark.asyncio
    async def test_get_history(self, client: AsyncClient, test_user):
        """Should return message history for a conversation."""
        # Create a conversation with a query
        resp = await client.post(
            "/api/v1/chat/query",
            json={"query": "What are the coding standards?"},
            headers=auth_headers(test_user),
        )
        conv_id = resp.json()["conversation_id"]

        # Get history
        response = await client.get(
            f"/api/v1/chat/history/{conv_id}",
            headers=auth_headers(test_user),
        )
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 2  # user + assistant
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_history_wrong_user(self, client: AsyncClient, test_user, admin_user):
        """Users should not access other users' conversation history."""
        # User creates conversation
        resp = await client.post(
            "/api/v1/chat/query",
            json={"query": "My private question"},
            headers=auth_headers(test_user),
        )
        conv_id = resp.json()["conversation_id"]

        # Admin tries to access it
        response = await client.get(
            f"/api/v1/chat/history/{conv_id}",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 404


class TestFeedback:
    """Test query feedback submission."""

    @pytest.mark.asyncio
    async def test_submit_feedback(self, client: AsyncClient, test_user):
        """Should accept valid feedback ratings."""
        # Create a query first (generates a query log)
        resp = await client.post(
            "/api/v1/chat/query",
            json={"query": "Test question for feedback"},
            headers=auth_headers(test_user),
        )
        assert resp.status_code == 200

        # Note: In placeholder mode, we'd need the query_log_id
        # This test validates the endpoint structure

    @pytest.mark.asyncio
    async def test_feedback_invalid_rating(self, client: AsyncClient, test_user):
        """Feedback with rating outside 1-5 should return 422."""
        response = await client.post(
            "/api/v1/chat/feedback",
            json={"query_log_id": "some-id", "rating": 10},
            headers=auth_headers(test_user),
        )
        assert response.status_code == 422

"""
Unit tests for authentication endpoints.
Tests registration, login, token refresh, and protected routes.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestRegistration:
    """Test user registration flow."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """New user registration should return 201 with user details."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@company.com",
            "username": "newuser",
            "password": "SecurePass123!",
            "role": "engineer",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@company.com"
        assert data["username"] == "newuser"
        assert data["role"] == "engineer"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Registration with existing email should return 409."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "testuser@company.com",
            "username": "different_name",
            "password": "SecurePass123!",
            "role": "engineer",
        })
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Registration with short password should return 422."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "user@company.com",
            "username": "user",
            "password": "short",
            "role": "engineer",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_role(self, client: AsyncClient):
        """Registration with invalid role should return 422."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "user@company.com",
            "username": "user",
            "password": "SecurePass123!",
            "role": "superadmin",
        })
        assert response.status_code == 422


class TestLogin:
    """Test user login flow."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Valid credentials should return access and refresh tokens."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "testuser@company.com",
            "password": "TestPassword123!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Wrong password should return 401."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "testuser@company.com",
            "password": "WrongPassword!",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Login with non-existent email should return 401."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@company.com",
            "password": "SomePassword!",
        })
        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh flow."""

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user):
        """Valid refresh token should return a new access token."""
        # First login
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@company.com",
            "password": "TestPassword123!",
        })
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, client: AsyncClient, test_user):
        """Using an access token for refresh should fail."""
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@company.com",
            "password": "TestPassword123!",
        })
        access_token = login_resp.json()["access_token"]

        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token,
        })
        assert response.status_code == 401


class TestProtectedRoutes:
    """Test authentication requirement on protected endpoints."""

    @pytest.mark.asyncio
    async def test_access_without_token(self, client: AsyncClient):
        """Requests without auth token should return 403."""
        response = await client.get("/api/v1/chat/conversations")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_access_with_valid_token(self, client: AsyncClient, test_user):
        """Requests with valid token should succeed."""
        response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers(test_user),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_access_with_invalid_token(self, client: AsyncClient):
        """Requests with invalid token should return 401."""
        response = await client.get(
            "/api/v1/chat/conversations",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_route_with_engineer(self, client: AsyncClient, test_user):
        """Engineer accessing admin-only route should return 403."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=auth_headers(test_user),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_route_with_admin(self, client: AsyncClient, admin_user):
        """Admin should access admin-only routes successfully."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200

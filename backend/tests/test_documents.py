"""
Unit tests for document management endpoints.
Tests upload, listing, metadata update, and deletion.
"""

import io

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestDocumentUpload:
    """Test document upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_txt_file(self, client: AsyncClient, admin_user):
        """Admin should be able to upload a .txt document."""
        file_content = b"This is a test document with sample content for testing."
        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test_doc.txt", io.BytesIO(file_content), "text/plain")},
            data={"department": "engineering", "doc_type": "manual"},
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["original_filename"] == "test_doc.txt"
        assert data["file_type"] == "txt"
        assert data["department"] == "engineering"
        assert data["status"] in ["processing", "ready"]

    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, client: AsyncClient, admin_user):
        """Uploading unsupported file type should return 400."""
        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("image.png", io.BytesIO(b"fake png"), "image/png")},
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_requires_admin_or_hr(self, client: AsyncClient, test_user):
        """Engineers should not be able to upload documents."""
        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("doc.txt", io.BytesIO(b"content"), "text/plain")},
            headers=auth_headers(test_user),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hr_can_upload(self, client: AsyncClient, hr_user):
        """HR role should be able to upload documents."""
        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("policy.txt", io.BytesIO(b"HR policy content"), "text/plain")},
            data={"department": "hr"},
            headers=auth_headers(hr_user),
        )
        assert response.status_code == 201


class TestDocumentListing:
    """Test document listing and retrieval."""

    @pytest.mark.asyncio
    async def test_list_documents(self, client: AsyncClient, test_user):
        """Any authenticated user should be able to list documents."""
        response = await client.get(
            "/api/v1/documents/",
            headers=auth_headers(test_user),
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_filter_by_department(self, client: AsyncClient, admin_user):
        """Should filter documents by department."""
        # Upload a document first
        await client.post(
            "/api/v1/documents/upload",
            files={"file": ("eng_doc.txt", io.BytesIO(b"Engineering doc"), "text/plain")},
            data={"department": "engineering"},
            headers=auth_headers(admin_user),
        )

        response = await client.get(
            "/api/v1/documents/?department=engineering",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        docs = response.json()
        for doc in docs:
            assert doc["department"] == "engineering"

    @pytest.mark.asyncio
    async def test_get_single_document(self, client: AsyncClient, admin_user):
        """Should retrieve a single document by ID."""
        # Upload
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("detail.txt", io.BytesIO(b"Detailed content"), "text/plain")},
            headers=auth_headers(admin_user),
        )
        doc_id = upload_resp.json()["id"]

        # Get
        response = await client.get(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        assert response.json()["id"] == doc_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, client: AsyncClient, test_user):
        """Requesting non-existent document should return 404."""
        response = await client.get(
            "/api/v1/documents/nonexistent-id",
            headers=auth_headers(test_user),
        )
        assert response.status_code == 404


class TestDocumentManagement:
    """Test metadata update and document deletion."""

    @pytest.mark.asyncio
    async def test_update_metadata(self, client: AsyncClient, admin_user):
        """Admin should update document metadata."""
        # Upload
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("update_test.txt", io.BytesIO(b"Content"), "text/plain")},
            headers=auth_headers(admin_user),
        )
        doc_id = upload_resp.json()["id"]

        # Update
        response = await client.patch(
            f"/api/v1/documents/{doc_id}/metadata",
            json={"department": "legal", "doc_type": "policy", "tags": ["compliance", "2025"]},
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        assert response.json()["department"] == "legal"

    @pytest.mark.asyncio
    async def test_delete_document(self, client: AsyncClient, admin_user):
        """Admin should delete a document."""
        # Upload
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("delete_me.txt", io.BytesIO(b"To be deleted"), "text/plain")},
            headers=auth_headers(admin_user),
        )
        doc_id = upload_resp.json()["id"]

        # Delete
        response = await client.delete(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 204

        # Verify deleted
        get_resp = await client.get(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers(admin_user),
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_requires_admin(self, client: AsyncClient, admin_user, hr_user):
        """Only admin should delete documents."""
        # Upload as admin
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("protected.txt", io.BytesIO(b"Protected"), "text/plain")},
            headers=auth_headers(admin_user),
        )
        doc_id = upload_resp.json()["id"]

        # HR tries to delete
        response = await client.delete(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers(hr_user),
        )
        assert response.status_code == 403

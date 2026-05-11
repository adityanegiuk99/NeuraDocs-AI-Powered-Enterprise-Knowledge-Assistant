"""
Document management API routes.
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import allow_admin, allow_admin_hr, get_current_user
from app.config import settings
from app.core.tasks import run_ingestion_pipeline
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentMetadataUpdate, DocumentResponse
from app.utils.logging import get_logger

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department: str = Form(None),
    doc_type: str = Form(None),
    author: str = Form(None),
    tags: str = Form(None),  # comma-separated
    current_user: User = Depends(allow_admin_hr),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for processing. Restricted to admin and HR roles."""
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not supported. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB",
        )

    # Save file to disk
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    upload_path = Path(settings.upload_dir) / filename
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Create document record
    doc = Document(
        id=file_id,
        filename=filename,
        original_filename=file.filename,
        file_type=ext.lstrip("."),
        file_size=len(content),
        department=department,
        doc_type=doc_type,
        author=author,
        tags=json.dumps(tag_list) if tag_list else None,
        uploaded_by=current_user.id,
        status="processing",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    logger.info(
        "document_uploaded",
        doc_id=doc.id,
        filename=file.filename,
        size=len(content),
        user_id=current_user.id,
    )

    # Trigger async ingestion pipeline in the background
    embedding_service = getattr(request.app.state, "embedding_service", None)
    vector_store = getattr(request.app.state, "vector_store", None)
    background_tasks.add_task(
        run_ingestion_pipeline,
        document_id=doc.id,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    return doc



@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    department: str = None,
    doc_type: str = None,
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents with optional filtering."""
    query = select(Document).order_by(Document.created_at.desc())

    if department:
        query = query.where(Document.department == department)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    if status_filter:
        query = query.where(Document.status == status_filter)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific document's details."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch("/{doc_id}/metadata", response_model=DocumentResponse)
async def update_metadata(
    doc_id: str,
    data: DocumentMetadataUpdate,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update document metadata. Admin only."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if data.department is not None:
        doc.department = data.department
    if data.doc_type is not None:
        doc.doc_type = data.doc_type
    if data.author is not None:
        doc.author = data.author
    if data.tags is not None:
        doc.tags = json.dumps(data.tags)

    await db.flush()
    await db.refresh(doc)

    logger.info("document_metadata_updated", doc_id=doc_id, user_id=current_user.id)
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its vectors. Admin only."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    file_path = Path(settings.upload_dir) / doc.filename
    if file_path.exists():
        file_path.unlink()

    # TODO: Remove vectors from FAISS index

    await db.delete(doc)
    logger.info("document_deleted", doc_id=doc_id, user_id=current_user.id)

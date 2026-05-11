"""
Background task runners for async document processing.
Uses FastAPI's BackgroundTasks for lightweight async operations.
"""

import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ingestion.pipeline import IngestionPipeline
from app.db.session import async_session
from app.models.document import Document
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def run_ingestion_pipeline(
    document_id: str,
    embedding_service=None,
    vector_store=None,
):
    """
    Background task: Run the full ingestion pipeline for a document.

    This is invoked as a FastAPI BackgroundTask after document upload.
    It runs in its own database session to avoid blocking the response.

    Pipeline: parse → chunk → embed → store in FAISS
    """
    async with async_session() as db:
        try:
            # Fetch the document
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                logger.error("ingestion_task_document_not_found", doc_id=document_id)
                return

            if document.status != "processing":
                logger.warning(
                    "ingestion_task_skipped",
                    doc_id=document_id,
                    status=document.status,
                )
                return

            logger.info(
                "ingestion_task_started",
                doc_id=document_id,
                filename=document.original_filename,
            )

            # Initialize pipeline
            pipeline = IngestionPipeline(
                embedding_service=embedding_service,
                vector_store=vector_store,
            )

            # Run ingestion
            chunk_count = await pipeline.ingest(document, db)

            await db.commit()

            logger.info(
                "ingestion_task_complete",
                doc_id=document_id,
                chunks=chunk_count,
            )

        except Exception as e:
            await db.rollback()
            logger.error(
                "ingestion_task_failed",
                doc_id=document_id,
                error=str(e),
            )
            # Try to mark the document as failed
            try:
                result = await db.execute(
                    select(Document).where(Document.id == document_id)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "failed"
                    doc.error_message = f"Background ingestion failed: {str(e)}"
                    await db.commit()
            except Exception:
                logger.error("ingestion_status_update_failed", doc_id=document_id)


async def reprocess_failed_documents(
    embedding_service=None,
    vector_store=None,
):
    """
    Utility task: Retry ingestion for all documents with 'failed' status.
    Can be triggered from admin endpoints.
    """
    async with async_session() as db:
        result = await db.execute(
            select(Document).where(Document.status == "failed")
        )
        failed_docs = result.scalars().all()

        if not failed_docs:
            logger.info("no_failed_documents_to_reprocess")
            return 0

        logger.info("reprocessing_failed_documents", count=len(failed_docs))

        reprocessed = 0
        for doc in failed_docs:
            doc.status = "processing"
            doc.error_message = None
            await db.flush()

            try:
                pipeline = IngestionPipeline(
                    embedding_service=embedding_service,
                    vector_store=vector_store,
                )
                await pipeline.ingest(doc, db)
                reprocessed += 1
            except Exception as e:
                logger.error(
                    "reprocessing_failed",
                    doc_id=doc.id,
                    error=str(e),
                )

        await db.commit()
        logger.info("reprocessing_complete", total=len(failed_docs), success=reprocessed)
        return reprocessed


async def cleanup_orphaned_files():
    """
    Utility task: Remove uploaded files that have no matching database record.
    Prevents storage leaks from failed uploads.
    """
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.exists():
        return 0

    async with async_session() as db:
        # Get all filenames from database
        result = await db.execute(select(Document.filename))
        db_filenames = {row[0] for row in result.all()}

        # Find orphaned files
        removed = 0
        for file_path in upload_dir.iterdir():
            if file_path.is_file() and file_path.name not in db_filenames:
                file_path.unlink()
                removed += 1
                logger.info("orphaned_file_removed", filename=file_path.name)

        logger.info("cleanup_complete", orphaned_removed=removed)
        return removed

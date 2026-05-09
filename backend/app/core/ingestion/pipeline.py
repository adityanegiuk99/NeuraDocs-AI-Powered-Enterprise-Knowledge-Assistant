"""
Document ingestion pipeline.
Orchestrates: parse → chunk → embed → store
"""

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ingestion.chunker import SmartChunker
from app.core.ingestion.metadata import MetadataExtractor
from app.core.ingestion.parser import DocumentParser
from app.models.document import Document
from app.utils.logging import get_logger

logger = get_logger(__name__)


class IngestionPipeline:
    """
    Full document ingestion pipeline.
    Takes a raw document, processes it through parsing, chunking,
    embedding, and stores results in the vector database.
    """

    def __init__(self, embedding_service=None, vector_store=None):
        self.parser = DocumentParser()
        self.chunker = SmartChunker()
        self.metadata_extractor = MetadataExtractor()
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def ingest(
        self,
        document: Document,
        db: AsyncSession,
    ) -> int:
        """
        Run the full ingestion pipeline for a document.
        Returns the number of chunks created.
        """
        file_path = Path(settings.upload_dir) / document.filename

        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        try:
            logger.info("ingestion_started", doc_id=document.id, file=document.original_filename)

            # Step 1: Parse document into structural elements
            elements = self.parser.parse(str(file_path))
            if not elements:
                document.status = "failed"
                document.error_message = "No content extracted from document"
                await db.flush()
                return 0

            # Step 2: Extract metadata
            content_preview = " ".join(e.text for e in elements[:10])  # First 10 elements
            user_meta = {}
            if document.department:
                user_meta["department"] = document.department
            if document.doc_type:
                user_meta["doc_type"] = document.doc_type
            if document.author:
                user_meta["author"] = document.author
            if document.tags:
                user_meta["tags"] = json.loads(document.tags)

            doc_metadata = self.metadata_extractor.extract(
                str(file_path), content_preview, user_meta
            )

            # Auto-fill document metadata if not provided by user
            if not document.department and doc_metadata.get("department"):
                document.department = doc_metadata["department"]
            if not document.doc_type and doc_metadata.get("doc_type"):
                document.doc_type = doc_metadata["doc_type"]

            # Step 3: Chunk the document
            chunks = self.chunker.chunk(
                elements=elements,
                document_id=document.id,
                doc_metadata=doc_metadata,
            )

            if not chunks:
                document.status = "failed"
                document.error_message = "No chunks produced from document"
                await db.flush()
                return 0

            # Step 4: Generate embeddings
            if self.embedding_service:
                texts = [chunk.text for chunk in chunks]
                embeddings = self.embedding_service.embed_texts(texts)

                # Step 5: Store in vector database
                if self.vector_store:
                    chunk_metadata = []
                    for chunk in chunks:
                        chunk_metadata.append({
                            "chunk_id": chunk.chunk_id,
                            "document_id": chunk.document_id,
                            "document_title": document.original_filename,
                            "section_heading": chunk.section_heading,
                            "page_number": chunk.page_number,
                            "chunk_index": chunk.chunk_index,
                            "element_type": chunk.element_type,
                            "token_count": chunk.token_count,
                            "text": chunk.text,
                            **{k: v for k, v in doc_metadata.items()
                               if k not in ("detected_dates", "file_size_bytes")},
                        })

                    self.vector_store.add(embeddings, chunk_metadata)
                    logger.info("vectors_stored", count=len(embeddings), doc_id=document.id)

            # Update document status
            document.chunk_count = len(chunks)
            document.status = "ready"
            await db.flush()

            logger.info(
                "ingestion_complete",
                doc_id=document.id,
                elements=len(elements),
                chunks=len(chunks),
            )

            return len(chunks)

        except Exception as e:
            document.status = "failed"
            document.error_message = str(e)
            await db.flush()
            logger.error("ingestion_failed", doc_id=document.id, error=str(e))
            raise

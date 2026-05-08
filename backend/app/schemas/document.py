"""
Document request/response schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    department: Optional[str] = None
    doc_type: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[str] = None
    uploaded_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentMetadataUpdate(BaseModel):
    department: Optional[str] = None
    doc_type: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[list[str]] = None


class ChunkResponse(BaseModel):
    chunk_id: int
    text: str
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    element_type: str
    token_count: int
    metadata: dict = {}

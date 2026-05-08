"""
Document database model for tracking uploaded documents.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf, docx, txt
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    status: Mapped[str] = mapped_column(
        Enum("processing", "ready", "failed", name="doc_status"),
        default="processing",
        nullable=False,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata fields
    department: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=True, index=True)  # policy, manual, faq
    author: Mapped[str] = mapped_column(String(200), nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=True)  # JSON-encoded list

    # Tracking
    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.original_filename}, status={self.status})>"

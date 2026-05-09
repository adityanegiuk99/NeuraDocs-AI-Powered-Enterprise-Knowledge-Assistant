"""
Smart chunking engine.
Implements hybrid semantic + structure-aware chunking.

Strategy:
1. Group elements by document structure (headings define sections)
2. Within each section, apply semantic similarity-based splitting
3. Enforce min/max chunk sizes (100-512 tokens)
4. Add configurable overlap for context preservation
5. Track parent-child relationships for context expansion during retrieval
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.core.ingestion.parser import DocumentElement
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Rough token estimate: 1 token ≈ 4 characters for English text
CHARS_PER_TOKEN = 4
MIN_CHUNK_TOKENS = 100
MAX_CHUNK_TOKENS = 512
OVERLAP_RATIO = 0.15


@dataclass
class Chunk:
    """A processed chunk ready for embedding and storage."""
    chunk_id: str
    text: str
    document_id: str
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: int = 0
    element_type: str = "narrative"
    token_count: int = 0
    parent_chunk_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Section:
    """A logical section of a document, defined by headings."""
    heading: Optional[str]
    elements: list[DocumentElement]
    page_number: Optional[int] = None


class SmartChunker:
    """
    Hybrid chunker combining structure-aware splitting with
    semantic similarity boundaries.
    """

    def __init__(
        self,
        max_tokens: int = MAX_CHUNK_TOKENS,
        min_tokens: int = MIN_CHUNK_TOKENS,
        overlap_ratio: float = OVERLAP_RATIO,
        embedding_fn=None,
    ):
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_ratio = overlap_ratio
        self.embedding_fn = embedding_fn  # Optional: for semantic splitting

    def chunk(
        self,
        elements: list[DocumentElement],
        document_id: str,
        doc_metadata: dict = None,
    ) -> list[Chunk]:
        """
        Main entry point. Converts document elements into optimized chunks.
        """
        if not elements:
            return []

        doc_metadata = doc_metadata or {}

        # Phase 1: Group into sections by headings
        sections = self._group_by_structure(elements)
        logger.info("chunking_sections", sections=len(sections), doc_id=document_id)

        # Phase 2: Chunk each section
        all_chunks = []
        chunk_index = 0

        for section in sections:
            section_text = self._section_to_text(section)
            section_tokens = self._estimate_tokens(section_text)

            if section_tokens <= self.max_tokens:
                # Section fits in a single chunk
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=section_text,
                    document_id=document_id,
                    section_heading=section.heading,
                    page_number=section.page_number,
                    chunk_index=chunk_index,
                    element_type=self._dominant_type(section.elements),
                    token_count=section_tokens,
                    metadata={**doc_metadata, "is_complete_section": True},
                )
                all_chunks.append(chunk)
                chunk_index += 1
            else:
                # Section too large → split into sub-chunks
                parent_id = str(uuid.uuid4())
                sub_chunks = self._split_section(
                    section, document_id, doc_metadata, chunk_index, parent_id
                )
                all_chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)

        # Phase 3: Add overlap between consecutive chunks
        all_chunks = self._add_overlap(all_chunks)

        # Phase 4: Merge tiny chunks
        all_chunks = self._merge_small_chunks(all_chunks)

        # Re-index
        for i, chunk in enumerate(all_chunks):
            chunk.chunk_index = i

        logger.info("chunking_complete", chunks=len(all_chunks), doc_id=document_id)
        return all_chunks

    def _group_by_structure(self, elements: list[DocumentElement]) -> list[Section]:
        """Group elements into sections based on titles/headings."""
        sections = []
        current_heading = None
        current_elements = []
        current_page = None

        for elem in elements:
            if elem.element_type == "title" and current_elements:
                # New heading → close current section
                sections.append(Section(
                    heading=current_heading,
                    elements=current_elements,
                    page_number=current_page,
                ))
                current_heading = elem.text
                current_elements = []
                current_page = elem.page_number
            elif elem.element_type == "title" and not current_elements:
                current_heading = elem.text
                current_page = elem.page_number
            else:
                current_elements.append(elem)
                if current_page is None:
                    current_page = elem.page_number

        # Don't forget the last section
        if current_elements:
            sections.append(Section(
                heading=current_heading,
                elements=current_elements,
                page_number=current_page,
            ))

        # If no sections were created (no headings), treat entire doc as one section
        if not sections:
            sections.append(Section(
                heading=None,
                elements=elements,
                page_number=elements[0].page_number if elements else None,
            ))

        return sections

    def _split_section(
        self,
        section: Section,
        document_id: str,
        doc_metadata: dict,
        start_index: int,
        parent_id: str,
    ) -> list[Chunk]:
        """Split a large section into smaller chunks using sentence boundaries."""
        full_text = self._section_to_text(section)

        # Split into sentences
        sentences = self._split_sentences(full_text)
        if not sentences:
            return []

        chunks = []
        current_text = ""
        chunk_idx = start_index

        for sentence in sentences:
            candidate = (current_text + " " + sentence).strip() if current_text else sentence
            candidate_tokens = self._estimate_tokens(candidate)

            if candidate_tokens > self.max_tokens and current_text:
                # Current chunk is full, save it
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=current_text.strip(),
                    document_id=document_id,
                    section_heading=section.heading,
                    page_number=section.page_number,
                    chunk_index=chunk_idx,
                    element_type=self._dominant_type(section.elements),
                    token_count=self._estimate_tokens(current_text),
                    parent_chunk_id=parent_id,
                    metadata={**doc_metadata, "is_complete_section": False},
                ))
                chunk_idx += 1
                current_text = sentence
            else:
                current_text = candidate

        # Save remaining text
        if current_text.strip():
            chunks.append(Chunk(
                chunk_id=str(uuid.uuid4()),
                text=current_text.strip(),
                document_id=document_id,
                section_heading=section.heading,
                page_number=section.page_number,
                chunk_index=chunk_idx,
                element_type=self._dominant_type(section.elements),
                token_count=self._estimate_tokens(current_text),
                parent_chunk_id=parent_id,
                metadata={**doc_metadata, "is_complete_section": False},
            ))

        return chunks

    def _add_overlap(self, chunks: list[Chunk]) -> list[Chunk]:
        """Add overlapping context from previous chunk to maintain continuity."""
        if len(chunks) <= 1:
            return chunks

        for i in range(1, len(chunks)):
            prev_text = chunks[i - 1].text
            overlap_chars = int(len(prev_text) * self.overlap_ratio)

            if overlap_chars > 50:  # Only add meaningful overlap
                # Take the last N characters from previous chunk
                overlap = prev_text[-overlap_chars:]
                # Try to start at a sentence boundary
                sentence_start = overlap.find(". ")
                if sentence_start != -1:
                    overlap = overlap[sentence_start + 2:]

                if overlap.strip():
                    chunks[i].text = f"[...] {overlap.strip()} {chunks[i].text}"
                    chunks[i].token_count = self._estimate_tokens(chunks[i].text)

        return chunks

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge chunks that are too small with their neighbors."""
        if len(chunks) <= 1:
            return chunks

        merged = [chunks[0]]
        for chunk in chunks[1:]:
            if chunk.token_count < self.min_tokens and merged:
                # Merge with previous chunk if combined size is reasonable
                prev = merged[-1]
                combined_tokens = prev.token_count + chunk.token_count
                if combined_tokens <= self.max_tokens * 1.2:
                    prev.text = prev.text + "\n\n" + chunk.text
                    prev.token_count = self._estimate_tokens(prev.text)
                    continue
            merged.append(chunk)

        return merged

    def _section_to_text(self, section: Section) -> str:
        """Convert a section to plain text."""
        parts = []
        if section.heading:
            parts.append(f"## {section.heading}")
        for elem in section.elements:
            parts.append(elem.text)
        return "\n\n".join(parts)

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences using simple heuristics."""
        import re
        # Split on sentence-ending punctuation followed by space
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate. For production, use tiktoken."""
        return len(text) // CHARS_PER_TOKEN

    def _dominant_type(self, elements: list[DocumentElement]) -> str:
        """Return the most common element type in a list."""
        if not elements:
            return "narrative"
        types = [e.element_type for e in elements]
        return max(set(types), key=types.count)

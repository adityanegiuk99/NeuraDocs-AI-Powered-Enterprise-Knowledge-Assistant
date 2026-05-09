"""
Metadata extraction and tagging for documents.
Extracts author, department, dates, and document type from content and file properties.
"""

import re
from datetime import date
from pathlib import Path
from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


class MetadataExtractor:
    """
    Extracts and enriches metadata for documents.
    Combines explicit user-provided metadata with auto-detected properties.
    """

    # Patterns for auto-detection
    DATE_PATTERNS = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
    ]

    DOC_TYPE_KEYWORDS = {
        "policy": ["policy", "regulation", "compliance", "guidelines", "rules"],
        "manual": ["manual", "handbook", "guide", "tutorial", "instructions"],
        "faq": ["faq", "frequently asked", "q&a", "questions and answers"],
        "report": ["report", "analysis", "summary", "findings", "quarterly", "annual"],
        "memo": ["memo", "memorandum", "notice", "announcement"],
        "sop": ["procedure", "sop", "standard operating", "process", "workflow"],
    }

    DEPARTMENT_KEYWORDS = {
        "hr": ["human resources", "hr ", "employee", "hiring", "benefits", "leave", "payroll"],
        "engineering": ["engineering", "technical", "development", "software", "architecture"],
        "finance": ["finance", "budget", "accounting", "revenue", "expenses", "fiscal"],
        "legal": ["legal", "compliance", "contract", "agreement", "liability"],
        "marketing": ["marketing", "brand", "campaign", "advertising", "social media"],
        "operations": ["operations", "logistics", "supply chain", "inventory"],
    }

    def extract(
        self,
        file_path: str,
        content_preview: str,
        user_metadata: dict = None,
    ) -> dict:
        """
        Extract metadata combining user-provided and auto-detected values.
        User-provided values always take precedence.
        """
        user_metadata = user_metadata or {}
        path = Path(file_path)

        metadata = {
            "filename": path.name,
            "file_extension": path.suffix.lower(),
            "file_size_bytes": path.stat().st_size if path.exists() else 0,
        }

        # Auto-detect doc_type from content
        if not user_metadata.get("doc_type"):
            metadata["doc_type"] = self._detect_doc_type(content_preview)
        else:
            metadata["doc_type"] = user_metadata["doc_type"]

        # Auto-detect department from content
        if not user_metadata.get("department"):
            metadata["department"] = self._detect_department(content_preview)
        else:
            metadata["department"] = user_metadata["department"]

        # Extract dates from content
        metadata["detected_dates"] = self._extract_dates(content_preview)

        # User-provided overrides
        if user_metadata.get("author"):
            metadata["author"] = user_metadata["author"]
        if user_metadata.get("tags"):
            metadata["tags"] = user_metadata["tags"]

        logger.info(
            "metadata_extracted",
            filename=path.name,
            doc_type=metadata.get("doc_type"),
            department=metadata.get("department"),
        )

        return metadata

    def _detect_doc_type(self, text: str) -> Optional[str]:
        """Auto-detect document type from content keywords."""
        text_lower = text.lower()
        scores = {}

        for doc_type, keywords in self.DOC_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[doc_type] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    def _detect_department(self, text: str) -> Optional[str]:
        """Auto-detect department from content keywords."""
        text_lower = text.lower()
        scores = {}

        for dept, keywords in self.DEPARTMENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[dept] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    def _extract_dates(self, text: str) -> list[str]:
        """Extract date strings from content."""
        dates = []
        for pattern in self.DATE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        return dates[:5]  # Return at most 5 dates

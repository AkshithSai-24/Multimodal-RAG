"""
Abstract base class for all document loaders.

Each loader returns a list of *raw* DocumentChunks.
The multimodal_processor then enriches them (vision summaries, chunking, etc.)
before they are stored in the vector-store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from models.document import DocumentChunk


class BaseLoader(ABC):
    """Every loader must implement `load` and return DocumentChunks."""

    @abstractmethod
    async def load(self, source: str, **kwargs) -> List[DocumentChunk]:
        """
        Load content from *source* (a URL, file path, ID, etc.).
        Returns a flat list of raw chunks (may still need further processing).
        """
        ...

    def _safe_str(self, value) -> str:
        """Coerce any value to a clean string."""
        if value is None:
            return ""
        return str(value).strip()

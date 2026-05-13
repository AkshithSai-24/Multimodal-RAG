"""
Internal document / chunk representation used throughout the pipeline.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    SLIDE = "slide"       # PowerPoint slide
    AUDIO_TRANSCRIPT = "audio_transcript"


class SourceType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    WEB = "web"
    IMAGE = "image"
    CSV = "csv"
    GDRIVE = "gdrive"
    YOUTUBE = "youtube"
    TEXT = "text"
    UNKNOWN = "unknown"


class DocumentChunk(BaseModel):
    """
    Unified chunk that holds one piece of retrieved / ingested content.

    *content*       – the text that gets embedded and stored in Chroma.
                      For images this is the vision-LLM summary.
    *image_base64*  – raw bytes of the image (base64-encoded) when present.
    *metadata*      – arbitrary key/value pairs forwarded to Chroma.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    modality: Modality = Modality.TEXT
    source_type: SourceType = SourceType.UNKNOWN
    source_id: str = ""          # URL, file path, Drive file-id, …
    source_name: str = ""        # human-readable label
    page_number: Optional[int] = None
    image_base64: Optional[str] = None   # only for IMAGE modality
    image_mime_type: str = "image/jpeg"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_chroma_metadata(self) -> Dict[str, Any]:
        """Flatten to a Chroma-compatible flat dict (no nested objects)."""
        meta = {
            "chunk_id": self.id,
            "modality": self.modality.value,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "image_mime_type": self.image_mime_type,
        }
        if self.page_number is not None:
            meta["page_number"] = self.page_number
        if self.image_base64:
            # Store truncated flag; full base64 kept in metadata dict below
            meta["has_image"] = True
            meta["image_base64"] = self.image_base64
        else:
            meta["has_image"] = False
        # Merge caller-supplied extras (must be scalar)
        for k, v in self.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                meta[k] = v
        return meta


class IngestedSource(BaseModel):
    """Summary returned after a successful ingestion."""

    source_id: str
    source_name: str
    source_type: SourceType
    total_chunks: int
    text_chunks: int
    image_chunks: int
    table_chunks: int
    collection_name: str


class RetrievedChunk(BaseModel):
    """A chunk surfaced by the retriever, enriched with its similarity score."""

    chunk_id: str
    content: str
    modality: Modality
    source_name: str
    source_type: SourceType
    page_number: Optional[int] = None
    has_image: bool = False
    image_base64: Optional[str] = None
    image_mime_type: str = "image/jpeg"
    score: float = 0.0


class RAGResponse(BaseModel):
    """Final answer + retrieved evidence returned to the caller."""

    answer: str
    sources: List[RetrievedChunk] = []
    model_used: str = ""
    total_tokens: int = 0

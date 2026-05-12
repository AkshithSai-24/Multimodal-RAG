"""
Loader Factory.

Maps source types and file extensions to the correct loader class.
Usage:
    loader = LoaderFactory.get(source_type=SourceType.PDF)
    # or auto-detect from path:
    loader = LoaderFactory.from_path("/tmp/report.pdf")
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Type

from loaders.base_loader import BaseLoader
from loaders.csv_loader import CSVLoader
from loaders.docx_loader import DOCXLoader
from loaders.image_loader import ImageLoader
from loaders.pdf_loader import PDFLoader
from loaders.pptx_loader import PPTXLoader
from loaders.web_loader import WebLoader
from loaders.youtube_loader import YouTubeLoader
from models.document import SourceType


_EXT_MAP: dict[str, Type[BaseLoader]] = {
    ".pdf": PDFLoader,
    ".docx": DOCXLoader,
    ".doc": DOCXLoader,
    ".pptx": PPTXLoader,
    ".ppt": PPTXLoader,
    ".jpg": ImageLoader,
    ".jpeg": ImageLoader,
    ".png": ImageLoader,
    ".gif": ImageLoader,
    ".webp": ImageLoader,
    ".bmp": ImageLoader,
    ".tiff": ImageLoader,
    ".csv": CSVLoader,
    ".tsv": CSVLoader,
    ".xlsx": CSVLoader,
    ".xls": CSVLoader,
    ".txt": None,      # handled inline
    ".md": None,       # handled inline
}

_TYPE_MAP: dict[SourceType, Type[BaseLoader]] = {
    SourceType.PDF: PDFLoader,
    SourceType.DOCX: DOCXLoader,
    SourceType.PPTX: PPTXLoader,
    SourceType.IMAGE: ImageLoader,
    SourceType.CSV: CSVLoader,
    SourceType.WEB: WebLoader,
    SourceType.YOUTUBE: YouTubeLoader,
}


class LoaderFactory:
    """Static factory for loader instances."""

    @staticmethod
    def get(source_type: SourceType, **kwargs) -> BaseLoader:
        cls = _TYPE_MAP.get(source_type)
        if cls is None:
            raise ValueError(f"No loader registered for source type: {source_type}")
        return cls(**kwargs)

    @staticmethod
    def from_path(file_path: str, **kwargs) -> Optional[BaseLoader]:
        """Detect loader from file extension.  Returns *None* for plain text."""
        ext = Path(file_path).suffix.lower()
        cls = _EXT_MAP.get(ext)
        if cls is None:
            return None
        return cls(**kwargs)

    @staticmethod
    def from_url(url: str, **kwargs) -> BaseLoader:
        """Detect loader from URL patterns."""
        if "youtube.com/watch" in url or "youtu.be/" in url:
            return YouTubeLoader(**kwargs)
        return WebLoader(**kwargs)

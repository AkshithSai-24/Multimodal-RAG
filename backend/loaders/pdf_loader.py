"""
PDF Loader.

Uses three complementary libraries:
  • pypdf          — fast text extraction per page
  • pdfplumber     — accurate table extraction per page
  • pymupdf (fitz) — image extraction per page

All three are run over every page so no content is missed.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import List

import fitz                        # pymupdf
import pdfplumber
from pypdf import PdfReader

from loaders.base_loader import BaseLoader
from models.document import DocumentChunk, Modality, SourceType


class PDFLoader(BaseLoader):
    """Load text, tables, and embedded images from a PDF file."""

    async def load(self, source: str, **kwargs) -> List[DocumentChunk]:
        path = Path(source)
        chunks: List[DocumentChunk] = []
        source_name = path.name

        # ── 1. Text (pypdf) ───────────────────────────────────────────────────
        reader = PdfReader(str(path))
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                chunks.append(
                    DocumentChunk(
                        content=text,
                        modality=Modality.TEXT,
                        source_type=SourceType.PDF,
                        source_id=str(path),
                        source_name=source_name,
                        page_number=page_num,
                    )
                )

        # ── 2. Tables (pdfplumber) ────────────────────────────────────────────
        with pdfplumber.open(str(path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for tbl_idx, table in enumerate(tables):
                    md = self._table_to_markdown(table)
                    if md:
                        chunks.append(
                            DocumentChunk(
                                content=md,
                                modality=Modality.TABLE,
                                source_type=SourceType.PDF,
                                source_id=str(path),
                                source_name=source_name,
                                page_number=page_num,
                                metadata={"table_index": tbl_idx},
                            )
                        )

        # ── 3. Images (pymupdf) ───────────────────────────────────────────────
        doc = fitz.open(str(path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            for img_idx, img_info in enumerate(page.get_images(full=True)):
                xref = img_info[0]
                try:
                    base_img = doc.extract_image(xref)
                    img_bytes = base_img["image"]
                    ext = base_img["ext"]
                    if len(img_bytes) < 4096:    # skip tiny images
                        continue
                    b64 = base64.b64encode(img_bytes).decode()
                    chunks.append(
                        DocumentChunk(
                            content=f"Image on page {page_num + 1} of {source_name}",
                            modality=Modality.IMAGE,
                            source_type=SourceType.PDF,
                            source_id=str(path),
                            source_name=source_name,
                            page_number=page_num + 1,
                            image_base64=b64,
                            image_mime_type=f"image/{ext}",
                            metadata={"image_index": img_idx},
                        )
                    )
                except Exception as exc:
                    print(f"[PDFLoader] Could not extract image xref={xref}: {exc}")
        doc.close()

        return chunks

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _table_to_markdown(table: List[List]) -> str:
        if not table or not table[0]:
            return ""
        rows = [[str(cell or "").strip() for cell in row] for row in table]
        # Header
        header = "| " + " | ".join(rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * len(rows[0])) + " |"
        body = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])
        return "\n".join(filter(None, [header, separator, body]))

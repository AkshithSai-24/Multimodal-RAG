"""
Multi-modal Processor Orchestrator.

Pipeline:
  raw chunks
      │
      ▼
  TextProcessor        — split large text/table chunks
      │
      ▼
  ImageProcessor       — vision-LLM summaries for image chunks
      │
      ▼
  TableProcessor       — LLM descriptions prepended to table chunks
      │
      ▼
  enriched chunks  →  stored in Chroma
"""

from __future__ import annotations

from typing import List

from models.document import DocumentChunk
from processors.image_processor import ImageProcessor
from processors.table_processor import TableProcessor
from processors.text_processor import TextProcessor


class MultiModalProcessor:
    """Orchestrate the full multi-modal enrichment pipeline."""

    def __init__(self):
        self._text = TextProcessor()
        self._image = ImageProcessor()
        self._table = TableProcessor()

    async def process(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Run the full pipeline on *chunks*.

        Steps are run sequentially to allow each processor to
        inspect the output of the previous one.
        """
        if not chunks:
            return []

        # 1. Split text / tables
        chunks = self._text.process(chunks)

        # 2. Generate vision summaries (async, batched)
        chunks = await self._image.process(chunks)

        # 3. Describe tables (async, batched)
        chunks = await self._table.process(chunks)

        # Filter out completely empty chunks
        chunks = [c for c in chunks if c.content.strip()]

        return chunks

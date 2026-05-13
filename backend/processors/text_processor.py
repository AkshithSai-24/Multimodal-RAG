"""
Text Processor — splits long text chunks into smaller pieces suitable for
embedding while preserving metadata and modality.
"""

from __future__ import annotations

from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings
from models.document import DocumentChunk, Modality


class TextProcessor:
    """Split TEXT and TABLE chunks into embedding-friendly sizes."""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""],
            length_function=len,
        )
        # Tables use a simpler splitter to avoid breaking rows
        self._table_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 2,
            chunk_overlap=0,
            separators=["\n\n", "\n"],
            length_function=len,
        )

    def process(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Split text / table chunks; pass IMAGE and SLIDE chunks through
        unchanged (they are handled by the image processor).
        """
        result: List[DocumentChunk] = []
        for chunk in chunks:
            if chunk.modality in (Modality.IMAGE, Modality.SLIDE):
                result.append(chunk)
                continue

            splitter = (
                self._table_splitter if chunk.modality == Modality.TABLE else self._splitter
            )

            if len(chunk.content) <= splitter._chunk_size:
                result.append(chunk)
                continue

            sub_texts = splitter.split_text(chunk.content)
            for i, sub_text in enumerate(sub_texts):
                new_chunk = chunk.model_copy(
                    update={
                        "content": sub_text,
                        "metadata": {**chunk.metadata, "sub_chunk_index": i},
                    }
                )
                # Generate a new deterministic ID based on parent + index
                import hashlib
                new_chunk.id = hashlib.md5(
                    f"{chunk.id}-{i}".encode()
                ).hexdigest()
                result.append(new_chunk)

        return result

"""
Image Processor.

For every IMAGE / SLIDE chunk that carries a base64 image, we call the
vision LLM to generate a rich textual summary.  That summary becomes the
*content* stored in Chroma (and thus what gets embedded and retrieved).
The raw base64 is preserved in metadata so it can be surfaced at query time.
"""

from __future__ import annotations

import asyncio
from typing import List

from langchain_core.messages import HumanMessage

from core.llm import get_vision_llm
from models.document import DocumentChunk, Modality

_VISION_PROMPT = (
    "You are a detail-oriented assistant helping build a multi-modal RAG system.\n"
    "Analyse the provided image and write a comprehensive description that includes:\n"
    "1. Overall subject and context\n"
    "2. All readable text, numbers, or labels visible\n"
    "3. Any charts, diagrams, graphs — describe their type, axes, and key data points\n"
    "4. Colours, layout, and visual hierarchy if relevant\n"
    "5. Any logos, icons, or notable visual elements\n\n"
    "Your description will be used as the searchable representation of this image "
    "in a retrieval system — be thorough and specific."
)

_MAX_CONCURRENT = 4     # parallel vision calls to avoid rate-limits


class ImageProcessor:
    """Generate vision summaries for image chunks."""

    async def process(self, chunks: List[DocumentChunk], use_vision_model: bool = True) -> List[DocumentChunk]:
        """
        Process all chunks; enrich IMAGE/SLIDE chunks that have a base64 payload
        with a vision-LLM summary. Non-image chunks pass through unchanged.
        When use_vision_model is False, return the chunks untouched.
        """
        if not use_vision_model:
            return chunks

        image_chunks = [
            c for c in chunks
            if c.modality in (Modality.IMAGE, Modality.SLIDE) and c.image_base64
        ]
        other_chunks = [
            c for c in chunks
            if not (c.modality in (Modality.IMAGE, Modality.SLIDE) and c.image_base64)
        ]

        if not image_chunks:
            return chunks

        # Batch with concurrency limit
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
        tasks = [self._summarise(chunk, semaphore) for chunk in image_chunks]
        enriched = await asyncio.gather(*tasks, return_exceptions=True)

        result = list(other_chunks)
        for original, enriched_or_exc in zip(image_chunks, enriched):
            if isinstance(enriched_or_exc, Exception):
                print(f"[ImageProcessor] Vision summary failed for {original.id}: {enriched_or_exc}")
                result.append(original)   # keep original placeholder
            else:
                result.append(enriched_or_exc)

        return result

    async def _summarise(
        self, chunk: DocumentChunk, semaphore: asyncio.Semaphore
    ) -> DocumentChunk:
        async with semaphore:
            llm = get_vision_llm()
            message = HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{chunk.image_mime_type};base64,{chunk.image_base64}"
                        },
                    },
                    {"type": "text", "text": _VISION_PROMPT},
                ]
            )
            response = await llm.ainvoke([message])
            summary = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )
            # Replace placeholder content with the rich summary
            return chunk.model_copy(update={"content": summary})

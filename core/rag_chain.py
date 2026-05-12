"""
Multi-modal RAG chain.

Flow
────
1.  Retrieve top-k chunks from Chroma (all modalities).
2.  Separate chunks by modality: text / table / image.
3.  Build a multi-modal HumanMessage:
      • text + table chunks → inline context blocks
      • image chunks → base64 image_url blocks (passed to the vision LLM)
4.  Invoke the vision-capable LLM and return the response.
"""

from __future__ import annotations

from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import settings
from core.llm import get_vision_llm
from core.vectorstore import VectorStoreManager
from models.document import Modality, RAGResponse, RetrievedChunk


SYSTEM_PROMPT = """You are a helpful AI assistant.
You have been given retrieved context that may include text passages, tables, and images.
Answer the user's question as accurately and concisely as possible, citing the sources when relevant.
If the context does not contain enough information to answer the question, say so clearly.
"""


def _build_text_context(chunks: List[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[Source {i} | {chunk.source_name} | {chunk.modality.value}]"
        if chunk.page_number:
            header += f" p.{chunk.page_number}"
        parts.append(f"{header}\n{chunk.content}")
    return "\n\n---\n\n".join(parts)


def _build_multimodal_content(
    query: str,
    text_chunks: List[RetrievedChunk],
    table_chunks: List[RetrievedChunk],
    image_chunks: List[RetrievedChunk],
    include_images: bool,
) -> list:
    """
    Assemble the OpenRouter / Anthropic vision message content list.
    Text and table context come first, then images, then the question.
    """
    content = []

    # ── Text + table context ─────────────────────────────────────────────────
    all_text = text_chunks + table_chunks
    if all_text:
        ctx_text = _build_text_context(all_text)
        content.append(
            {
                "type": "text",
                "text": f"## Retrieved Context\n\n{ctx_text}\n",
            }
        )

    # ── Image blocks ─────────────────────────────────────────────────────────
    if include_images and image_chunks:
        content.append(
            {
                "type": "text",
                "text": "## Retrieved Images (with their AI-generated summaries)\n",
            }
        )
        for img in image_chunks[: settings.MAX_IMAGE_DOCS]:
            # Include the vision summary as text
            summary_header = (
                f"[Image from: {img.source_name}"
                + (f" p.{img.page_number}" if img.page_number else "")
                + "]\n"
                + img.content  # vision LLM summary stored at ingest time
            )
            content.append({"type": "text", "text": summary_header})

            # Optionally attach the actual image for the LLM to re-inspect
            if img.image_base64:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img.image_mime_type};base64,{img.image_base64}"
                        },
                    }
                )

    # ── The question ─────────────────────────────────────────────────────────
    content.append({"type": "text", "text": f"## Question\n\n{query}"})

    return content


async def run_rag(
    query: str,
    vs_manager: VectorStoreManager,
    collection_name: Optional[str] = None,
    top_k: int = 6,
    include_images: bool = True,
    filters: Optional[dict] = None,
) -> RAGResponse:
    """
    Main entry-point for a RAG query.
    Returns a RAGResponse with the answer and retrieved sources.
    """
    # 1. Retrieve
    chunks: List[RetrievedChunk] = await vs_manager.similarity_search(
        query,
        collection_name=collection_name,
        k=top_k,
        where=filters,
    )

    if not chunks:
        return RAGResponse(
            answer="I couldn't find any relevant information in the knowledge base.",
            sources=[],
            model_used=settings.VISION_MODEL,
        )

    # 2. Separate modalities
    text_chunks = [c for c in chunks if c.modality == Modality.TEXT]
    table_chunks = [c for c in chunks if c.modality == Modality.TABLE]
    image_chunks = [c for c in chunks if c.modality in (Modality.IMAGE, Modality.SLIDE)]

    # 3. Build multi-modal message content
    message_content = _build_multimodal_content(
        query, text_chunks, table_chunks, image_chunks, include_images
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message_content),
    ]

    # 4. Invoke vision LLM
    llm = get_vision_llm()
    response = await llm.ainvoke(messages)

    answer_text = response.content if isinstance(response.content, str) else str(response.content)

    # 5. Token accounting (best-effort)
    total_tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        total_tokens = response.usage_metadata.get("total_tokens", 0)

    return RAGResponse(
        answer=answer_text,
        sources=chunks,
        model_used=settings.VISION_MODEL,
        total_tokens=total_tokens,
    )

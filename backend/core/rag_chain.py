"""
Multi-modal RAG chain.

Flow
────
1.  Retrieve top-k chunks from Chroma (all modalities).
2.  Separate chunks by modality: text / table / image.
3.  Build either:
      • a multimodal HumanMessage with text + image_url blocks when the
        vision toggle is ON, or
      • a plain text prompt when the vision toggle is OFF.
4.  Invoke the selected LLM and return the response.
"""

from __future__ import annotations

from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import settings
from core.llm import get_llm, get_vision_llm
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


def _build_text_prompt(
    query: str,
    text_chunks: List[RetrievedChunk],
    table_chunks: List[RetrievedChunk],
    image_chunks: List[RetrievedChunk],
    include_images: bool,
) -> str:
    sections: List[str] = []

    all_text = text_chunks + table_chunks
    if all_text:
        sections.append(f"## Retrieved Context\n\n{_build_text_context(all_text)}")

    if include_images and image_chunks:
        image_lines: List[str] = ["## Retrieved Images"]
        for img in image_chunks[: settings.MAX_IMAGE_DOCS]:
            summary_header = (
                f"[Image from: {img.source_name}"
                + (f" p.{img.page_number}" if img.page_number else "")
                + "]\n"
                + img.content
            )
            image_lines.append(summary_header)
        sections.append("\n\n".join(image_lines))

    sections.append(f"## Question\n\n{query}")
    return "\n\n---\n\n".join(sections)


def _build_multimodal_content(
    query: str,
    text_chunks: List[RetrievedChunk],
    table_chunks: List[RetrievedChunk],
    image_chunks: List[RetrievedChunk],
    include_images: bool,
) -> list:
    """Assemble the OpenRouter / vision message content list."""
    content = []

    all_text = text_chunks + table_chunks
    if all_text:
        ctx_text = _build_text_context(all_text)
        content.append(
            {
                "type": "text",
                "text": f"## Retrieved Context\n\n{ctx_text}\n",
            }
        )

    if include_images and image_chunks:
        content.append(
            {
                "type": "text",
                "text": "## Retrieved Images (with their AI-generated summaries)\n",
            }
        )
        for img in image_chunks[: settings.MAX_IMAGE_DOCS]:
            summary_header = (
                f"[Image from: {img.source_name}"
                + (f" p.{img.page_number}" if img.page_number else "")
                + "]\n"
                + img.content
            )
            content.append({"type": "text", "text": summary_header})

            if img.image_base64:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img.image_mime_type};base64,{img.image_base64}"
                        },
                    }
                )

    content.append({"type": "text", "text": f"## Question\n\n{query}"})
    return content


async def run_rag(
    query: str,
    vs_manager: VectorStoreManager,
    collection_name: Optional[str] = None,
    top_k: int = 6,
    include_images: bool = True,
    filters: Optional[dict] = None,
    use_vision_model: bool = True,
) -> RAGResponse:
    """Main entry-point for a RAG query."""
    chunks: List[RetrievedChunk] = await vs_manager.similarity_search(
        query,
        collection_name=collection_name,
        k=top_k,
        where=filters,
    )

    model_used = settings.VISION_MODEL if use_vision_model else settings.LLM_MODEL

    if not chunks:
        return RAGResponse(
            answer="I couldn't find any relevant information in the knowledge base.",
            sources=[],
            model_used=model_used,
        )

    text_chunks = [c for c in chunks if c.modality == Modality.TEXT]
    table_chunks = [c for c in chunks if c.modality == Modality.TABLE]
    image_chunks = [c for c in chunks if c.modality in (Modality.IMAGE, Modality.SLIDE)]

    if use_vision_model:
        message_content = _build_multimodal_content(
            query, text_chunks, table_chunks, image_chunks, include_images
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message_content),
        ]
        llm = get_vision_llm()
    else:
        prompt = _build_text_prompt(
            query, text_chunks, table_chunks, image_chunks, include_images
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        llm = get_llm()

    response = await llm.ainvoke(messages)
    answer_text = response.content if isinstance(response.content, str) else str(response.content)

    total_tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        total_tokens = response.usage_metadata.get("total_tokens", 0)

    return RAGResponse(
        answer=answer_text,
        sources=chunks,
        model_used=model_used,
        total_tokens=total_tokens,
    )

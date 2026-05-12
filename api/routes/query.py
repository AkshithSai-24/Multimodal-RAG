"""
Query routes.

POST /query          — run a multi-modal RAG query
POST /query/search   — raw similarity search (no LLM generation)
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from core.rag_chain import run_rag
from models.schemas import QueryRequest, QueryResponse

router = APIRouter()


@router.post("", response_model=QueryResponse)
async def query(body: QueryRequest, request: Request):
    """
    Run a multi-modal RAG query.

    Retrieves relevant text, table, and image chunks from Chroma,
    builds a multi-modal prompt, and returns the LLM answer along with
    the source chunks that were used.
    """
    vs = request.app.state.vs_manager
    use_vision_model = getattr(request.app.state, "use_vision_model", True)
    rag_response = await run_rag(
        query=body.query,
        vs_manager=vs,
        collection_name=body.collection_name,
        top_k=body.top_k,
        include_images=body.include_images,
        filters=body.filters,
        use_vision_model=use_vision_model,
    )

    sources_out = []
    for chunk in rag_response.sources:
        src = {
            "chunk_id": chunk.chunk_id,
            "content_preview": chunk.content[:300],
            "modality": chunk.modality.value,
            "source_name": chunk.source_name,
            "source_type": chunk.source_type.value,
            "score": round(chunk.score, 4),
        }
        if chunk.page_number:
            src["page_number"] = chunk.page_number
        if chunk.has_image and chunk.image_base64:
            src["has_image"] = True
            src["image_data"] = f"data:{chunk.image_mime_type};base64,{chunk.image_base64}"
        sources_out.append(src)

    return QueryResponse(
        answer=rag_response.answer,
        sources=sources_out,
        model_used=rag_response.model_used,
    )


@router.post("/search")
async def search(body: QueryRequest, request: Request):
    """
    Raw similarity search — returns matched chunks without LLM generation.
    Useful for debugging retrieval quality.
    """
    vs = request.app.state.vs_manager
    chunks = await vs.similarity_search(
        query=body.query,
        collection_name=body.collection_name,
        k=body.top_k,
        where=body.filters,
    )
    return {
        "query": body.query,
        "results": [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "modality": c.modality.value,
                "source_name": c.source_name,
                "score": round(c.score, 4),
                "has_image": c.has_image,
            }
            for c in chunks
        ],
    }

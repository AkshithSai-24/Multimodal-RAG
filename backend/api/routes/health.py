"""
Health check endpoints.
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    vs = request.app.state.vs_manager
    count = await vs.get_collection_count()
    return {"status": "ok", "default_collection_docs": count}


@router.get("/")
async def root():
    return {
        "name": "MultiModal RAG API",
        "version": "1.0.0",
        "docs": "/docs",
    }

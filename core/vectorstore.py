"""
Chroma vector-store manager.

Provides async-friendly wrappers around the synchronous langchain_chroma
client so they can be called from FastAPI endpoints without blocking the
event loop.
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Dict, List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

from config.settings import settings
from core.embeddings import get_embeddings
from models.document import DocumentChunk, RetrievedChunk, Modality, SourceType


class VectorStoreManager:
    """Wraps Chroma with async helpers and collection routing."""

    def __init__(self) -> None:
        self._stores: Dict[str, Chroma] = {}
        self._default_collection = settings.CHROMA_COLLECTION_NAME

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Pre-warm the default collection on startup."""
        await self._get_or_create(self._default_collection)

    async def _get_or_create(self, collection_name: str) -> Chroma:
        if collection_name not in self._stores:
            store = await asyncio.get_event_loop().run_in_executor(
                None,
                partial(
                    Chroma,
                    collection_name=collection_name,
                    embedding_function=get_embeddings(),
                    persist_directory=settings.CHROMA_PERSIST_DIR,
                ),
            )
            self._stores[collection_name] = store
        return self._stores[collection_name]

    # ── Write ─────────────────────────────────────────────────────────────────

    async def add_chunks(
        self,
        chunks: List[DocumentChunk],
        collection_name: Optional[str] = None,
    ) -> int:
        """
        Upsert *chunks* into Chroma. Returns the number of docs added.
        """
        col = collection_name or self._default_collection
        store = await self._get_or_create(col)

        lc_docs: List[Document] = []
        ids: List[str] = []

        for chunk in chunks:
            lc_docs.append(
                Document(
                    page_content=chunk.content,
                    metadata=chunk.to_chroma_metadata(),
                )
            )
            ids.append(chunk.id)

        if not lc_docs:
            return 0

        await asyncio.get_event_loop().run_in_executor(
            None, partial(store.add_documents, lc_docs, ids=ids)
        )
        return len(lc_docs)

    # ── Read ──────────────────────────────────────────────────────────────────

    async def similarity_search(
        self,
        query: str,
        collection_name: Optional[str] = None,
        k: int = 6,
        where: Optional[Dict] = None,
    ) -> List[RetrievedChunk]:
        """
        Run a similarity search and return hydrated RetrievedChunk objects.
        """
        col = collection_name or self._default_collection
        store = await self._get_or_create(col)

        search_kwargs: Dict = {"k": k}
        if where:
            search_kwargs["filter"] = where

        raw: List[Tuple[Document, float]] = await asyncio.get_event_loop().run_in_executor(
            None,
            partial(store.similarity_search_with_relevance_scores, query, **search_kwargs),
        )

        results: List[RetrievedChunk] = []
        for doc, score in raw:
            meta = doc.metadata
            results.append(
                RetrievedChunk(
                    chunk_id=meta.get("chunk_id", ""),
                    content=doc.page_content,
                    modality=Modality(meta.get("modality", "text")),
                    source_name=meta.get("source_name", ""),
                    source_type=SourceType(meta.get("source_type", "unknown")),
                    page_number=meta.get("page_number"),
                    has_image=meta.get("has_image", False),
                    image_base64=meta.get("image_base64"),
                    image_mime_type=meta.get("image_mime_type", "image/jpeg"),
                    score=float(score),
                )
            )
        return results

    # ── Collection management ────────────────────────────────────────────────

    async def list_collections(self) -> List[Dict]:
        """Return name + count for every known collection."""
        result = []
        for name, store in self._stores.items():
            count = await asyncio.get_event_loop().run_in_executor(
                None, store._collection.count
            )
            result.append({"name": name, "count": count, "metadata": {}})
        return result

    async def delete_collection(self, collection_name: str) -> bool:
        store = await self._get_or_create(collection_name)
        await asyncio.get_event_loop().run_in_executor(
            None, store.delete_collection
        )
        self._stores.pop(collection_name, None)
        return True

    async def get_collection_count(self, collection_name: Optional[str] = None) -> int:
        col = collection_name or self._default_collection
        store = await self._get_or_create(col)
        return await asyncio.get_event_loop().run_in_executor(
            None, store._collection.count
        )


# Module-level singleton — populated by lifespan in main.py
_manager: Optional[VectorStoreManager] = None


def get_vs_manager() -> VectorStoreManager:
    if _manager is None:
        raise RuntimeError("VectorStoreManager not initialised. Call init_vectorstore() first.")
    return _manager


async def init_vectorstore() -> VectorStoreManager:
    """Called once at startup from main.py lifespan."""
    global _manager
    _manager = VectorStoreManager()
    await _manager.initialize()
    return _manager

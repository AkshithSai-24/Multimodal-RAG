"""
Ingestion routes.

POST /ingest/file        — upload a file (PDF, DOCX, PPTX, image, CSV, …)
POST /ingest/url         — scrape a website
POST /ingest/gdrive      — import a Google Drive file by ID
POST /ingest/text        — ingest raw text
POST /ingest/youtube     — ingest a YouTube transcript

GET  /ingest/collections         — list Chroma collections
DELETE /ingest/collections/{name} — delete a collection
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from config.settings import settings
from loaders.loader_factory import LoaderFactory
from mcp.registry import get_mcp_registry
from models.document import IngestedSource, SourceType
from models.schemas import (
    DeleteCollectionRequest,
    IngestGDriveRequest,
    IngestTextRequest,
    IngestURLRequest,
    IngestYouTubeRequest,
    ListCollectionsResponse,
)
from processors.multimodal_processor import MultiModalProcessor
from utils.file_utils import save_upload_temp
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter()
_processor = MultiModalProcessor()


def _count_by_modality(chunks) -> dict:
    from models.document import Modality
    return {
        "text": sum(1 for c in chunks if c.modality == Modality.TEXT),
        "image": sum(1 for c in chunks if c.modality == Modality.IMAGE),
        "table": sum(1 for c in chunks if c.modality == Modality.TABLE),
        "slide": sum(1 for c in chunks if c.modality == Modality.SLIDE),
    }


# ── File upload ───────────────────────────────────────────────────────────────

@router.post("/file", response_model=IngestedSource)
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
):
    """Upload any supported file type for multi-modal ingestion."""
    tmp_path = await save_upload_temp(file)
    suffix = Path(tmp_path).suffix.lower()
    try:
        loader = LoaderFactory.from_path(tmp_path)
        if loader is None:
            raise HTTPException(400, f"Unsupported file type: {suffix}")
        log.info("Loading '%s' with %s", file.filename, type(loader).__name__)
        raw_chunks = await loader.load(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not raw_chunks:
        raise HTTPException(422, "No content could be extracted from the file.")

    enriched = await _processor.process(raw_chunks)
    vs = request.app.state.vs_manager
    added = await vs.add_chunks(enriched, collection_name=collection_name)
    counts = _count_by_modality(enriched)

    return IngestedSource(
        source_id=raw_chunks[0].source_id,
        source_name=file.filename or "upload",
        source_type=raw_chunks[0].source_type,
        total_chunks=added,
        text_chunks=counts["text"],
        image_chunks=counts["image"] + counts["slide"],
        table_chunks=counts["table"],
        collection_name=collection_name or settings.CHROMA_COLLECTION_NAME,
    )


# ── URL scraping ──────────────────────────────────────────────────────────────

@router.post("/url", response_model=IngestedSource)
async def ingest_url(body: IngestURLRequest, request: Request):
    """Scrape a website (optional shallow crawl) and ingest all content."""
    loader = LoaderFactory.from_url(body.url, max_depth=body.max_depth)
    raw_chunks = await loader.load(body.url, max_depth=body.max_depth)

    if not raw_chunks:
        raise HTTPException(422, "No content scraped from the URL.")

    enriched = await _processor.process(raw_chunks)
    vs = request.app.state.vs_manager
    added = await vs.add_chunks(enriched, collection_name=body.collection_name)
    counts = _count_by_modality(enriched)

    return IngestedSource(
        source_id=body.url,
        source_name=body.url,
        source_type=SourceType.WEB,
        total_chunks=added,
        text_chunks=counts["text"],
        image_chunks=counts["image"],
        table_chunks=counts["table"],
        collection_name=body.collection_name or settings.CHROMA_COLLECTION_NAME,
    )


# ── Google Drive ──────────────────────────────────────────────────────────────

@router.post("/gdrive", response_model=IngestedSource)
async def ingest_gdrive(body: IngestGDriveRequest, request: Request):
    """Import a Google Drive file by its file ID."""
    registry = get_mcp_registry()
    gdrive = registry.get_gdrive_client(access_token=body.access_token)

    try:
        raw_chunks = await gdrive.load_file(body.file_id)
    except Exception as exc:
        raise HTTPException(502, f"Google Drive error: {exc}") from exc

    if not raw_chunks:
        raise HTTPException(422, "No content found in the Drive file.")

    enriched = await _processor.process(raw_chunks)
    vs = request.app.state.vs_manager
    added = await vs.add_chunks(enriched, collection_name=body.collection_name)
    counts = _count_by_modality(enriched)

    name = raw_chunks[0].source_name if raw_chunks else body.file_id
    return IngestedSource(
        source_id=body.file_id,
        source_name=name,
        source_type=SourceType.GDRIVE,
        total_chunks=added,
        text_chunks=counts["text"],
        image_chunks=counts["image"],
        table_chunks=counts["table"],
        collection_name=body.collection_name or settings.CHROMA_COLLECTION_NAME,
    )


# ── Raw text ──────────────────────────────────────────────────────────────────

@router.post("/text", response_model=IngestedSource)
async def ingest_text(body: IngestTextRequest, request: Request):
    """Ingest a raw text string."""
    from models.document import DocumentChunk, Modality, SourceType as ST
    import uuid
    raw_chunks = [
        DocumentChunk(
            content=body.text,
            modality=Modality.TEXT,
            source_type=ST.TEXT,
            source_id=str(uuid.uuid4()),
            source_name=body.source_name,
        )
    ]
    enriched = await _processor.process(raw_chunks)
    vs = request.app.state.vs_manager
    added = await vs.add_chunks(enriched, collection_name=body.collection_name)

    return IngestedSource(
        source_id=raw_chunks[0].source_id,
        source_name=body.source_name,
        source_type=ST.TEXT,
        total_chunks=added,
        text_chunks=added,
        image_chunks=0,
        table_chunks=0,
        collection_name=body.collection_name or settings.CHROMA_COLLECTION_NAME,
    )


# ── YouTube ───────────────────────────────────────────────────────────────────

@router.post("/youtube", response_model=IngestedSource)
async def ingest_youtube(body: IngestYouTubeRequest, request: Request):
    """Fetch a YouTube transcript and ingest it."""
    from loaders.youtube_loader import YouTubeLoader
    loader = YouTubeLoader()
    try:
        raw_chunks = await loader.load(body.url)
    except Exception as exc:
        raise HTTPException(502, f"YouTube transcript error: {exc}") from exc

    if not raw_chunks:
        raise HTTPException(422, "No transcript available for this video.")

    enriched = await _processor.process(raw_chunks)
    vs = request.app.state.vs_manager
    added = await vs.add_chunks(enriched, collection_name=body.collection_name)

    return IngestedSource(
        source_id=body.url,
        source_name=raw_chunks[0].source_name if raw_chunks else body.url,
        source_type=SourceType.YOUTUBE,
        total_chunks=added,
        text_chunks=added,
        image_chunks=0,
        table_chunks=0,
        collection_name=body.collection_name or settings.CHROMA_COLLECTION_NAME,
    )


# ── Collection management ─────────────────────────────────────────────────────

@router.get("/collections", response_model=ListCollectionsResponse)
async def list_collections(request: Request):
    vs = request.app.state.vs_manager
    cols = await vs.list_collections()
    from models.schemas import CollectionInfo
    return ListCollectionsResponse(
        collections=[CollectionInfo(**c) for c in cols]
    )


@router.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str, request: Request):
    vs = request.app.state.vs_manager
    await vs.delete_collection(collection_name)
    return {"deleted": collection_name}

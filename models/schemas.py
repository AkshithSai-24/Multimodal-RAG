"""
FastAPI request / response Pydantic schemas.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


# ── Ingest schemas ────────────────────────────────────────────────────────────

class IngestURLRequest(BaseModel):
    url: str = Field(..., description="Full URL to scrape")
    max_depth: int = Field(1, ge=1, le=5, description="Crawl depth (1 = single page)")
    collection_name: Optional[str] = None
    use_vision_model: bool = Field(True, description="Use vision model during ingestion and query")

class IngestGDriveRequest(BaseModel):
    file_id: str = Field(..., description="Google Drive file ID")
    access_token: Optional[str] = Field(None, description="Override the server-level token")
    collection_name: Optional[str] = None
    use_vision_model: bool = Field(True, description="Use vision model during ingestion and query")

class IngestTextRequest(BaseModel):
    text: str = Field(..., description="Raw text to ingest")
    source_name: str = Field("manual-text", description="Friendly label")
    collection_name: Optional[str] = None
    use_vision_model: bool = Field(True, description="Use vision model during ingestion and query")

class IngestYouTubeRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    collection_name: Optional[str] = None
    use_vision_model: bool = Field(True, description="Use vision model during ingestion and query")


# ── Query schemas ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural-language question")
    collection_name: Optional[str] = None
    top_k: int = Field(6, ge=1, le=20)
    include_images: bool = True
    filters: Optional[Dict[str, Any]] = None    # passed to Chroma where-filter

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
    model_used: str = ""


# ── Collection schemas ────────────────────────────────────────────────────────

class CollectionInfo(BaseModel):
    name: str
    count: int
    metadata: Dict[str, Any] = {}

class ListCollectionsResponse(BaseModel):
    collections: List[CollectionInfo]

class DeleteCollectionRequest(BaseModel):
    collection_name: str

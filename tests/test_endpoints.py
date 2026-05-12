"""
Integration tests for HTTP endpoints.

These use FastAPI's TestClient (synchronous) and mock LLM / embedding calls
so no real API keys are needed.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch_embeddings():
    """Return a mock that produces deterministic float vectors."""
    mock = MagicMock()
    mock.embed_documents = MagicMock(return_value=[[0.1] * 384])
    mock.embed_query = MagicMock(return_value=[0.1] * 384)
    return mock


def _patch_vision_llm(answer: str = "Mocked answer"):
    mock_response = MagicMock()
    mock_response.content = answer
    mock_response.usage_metadata = {"total_tokens": 100}
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_root_endpoint(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "MultiModal RAG API" in resp.json()["name"]


# ── Ingest: text ──────────────────────────────────────────────────────────────

@patch("core.embeddings.get_embeddings")
def test_ingest_text(mock_emb, client: TestClient):
    mock_emb.return_value = _patch_embeddings()

    resp = client.post(
        "/ingest/text",
        json={"text": "This is a test document about AI.", "source_name": "test-doc"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_chunks"] >= 1
    assert body["source_type"] == "text"


# ── Ingest: file upload (PDF stub) ────────────────────────────────────────────

@patch("core.embeddings.get_embeddings")
@patch("loaders.pdf_loader.PdfReader")
@patch("loaders.pdf_loader.pdfplumber")
@patch("loaders.pdf_loader.fitz")
@patch("processors.image_processor.get_vision_llm")
@patch("processors.table_processor.get_llm")
def test_ingest_pdf_file(
    mock_text_llm,
    mock_vision_llm,
    mock_fitz,
    mock_pdfplumber,
    mock_pypdf,
    mock_emb,
    client: TestClient,
):
    # Embeddings
    mock_emb.return_value = _patch_embeddings()

    # PDF text page
    page_mock = MagicMock()
    page_mock.extract_text.return_value = "Extracted page text content here."
    mock_pypdf.return_value.pages = [page_mock]

    # pdfplumber tables
    plumber_page = MagicMock()
    plumber_page.extract_tables.return_value = []
    plumber_ctx = MagicMock()
    plumber_ctx.__enter__ = MagicMock(return_value=MagicMock(pages=[plumber_page]))
    plumber_ctx.__exit__ = MagicMock(return_value=False)
    mock_pdfplumber.open.return_value = plumber_ctx

    # pymupdf (no images)
    fitz_doc = MagicMock()
    fitz_doc.__len__ = MagicMock(return_value=1)
    fitz_page = MagicMock()
    fitz_page.get_images.return_value = []
    fitz_doc.__getitem__ = MagicMock(return_value=fitz_page)
    mock_fitz.open.return_value = fitz_doc

    # LLMs not needed (no images/tables)
    mock_vision_llm.return_value = _patch_vision_llm()
    mock_text_llm.return_value = _patch_vision_llm()

    fake_pdf = io.BytesIO(b"%PDF-1.4 fake content")
    resp = client.post(
        "/ingest/file",
        files={"file": ("test.pdf", fake_pdf, "application/pdf")},
    )
    # Status should be 200 (content extracted) or 422 (mock returned nothing usable)
    assert resp.status_code in (200, 422)


# ── Query ─────────────────────────────────────────────────────────────────────

@patch("core.rag_chain.get_vision_llm")
@patch("core.vectorstore.VectorStoreManager.similarity_search", new_callable=AsyncMock)
def test_query_empty_kb(mock_search, mock_llm, client: TestClient):
    mock_search.return_value = []
    mock_llm.return_value = _patch_vision_llm("No relevant information found.")

    resp = client.post(
        "/query",
        json={"query": "What is the capital of France?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body


@patch("core.rag_chain.get_vision_llm")
@patch("core.vectorstore.VectorStoreManager.similarity_search", new_callable=AsyncMock)
def test_query_search_only(mock_search, mock_llm, client: TestClient):
    from models.document import Modality, SourceType, RetrievedChunk
    mock_search.return_value = [
        RetrievedChunk(
            chunk_id="abc",
            content="Paris is the capital of France.",
            modality=Modality.TEXT,
            source_name="geography.pdf",
            source_type=SourceType.PDF,
            score=0.95,
        )
    ]
    mock_llm.return_value = _patch_vision_llm()

    resp = client.post(
        "/query/search",
        json={"query": "capital of France"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["score"] == 0.95

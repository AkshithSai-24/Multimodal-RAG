"""Tests for models/document.py"""

from models.document import (
    DocumentChunk,
    Modality,
    SourceType,
    RetrievedChunk,
)


def test_document_chunk_defaults():
    chunk = DocumentChunk(content="Hello world")
    assert chunk.modality == Modality.TEXT
    assert chunk.source_type == SourceType.UNKNOWN
    assert chunk.id  # auto-generated UUID


def test_document_chunk_chroma_metadata_flat():
    chunk = DocumentChunk(
        content="Test",
        modality=Modality.TABLE,
        source_type=SourceType.PDF,
        source_id="/tmp/report.pdf",
        source_name="report.pdf",
        page_number=3,
        metadata={"nested": {"should": "be skipped"}, "scalar": 42},
    )
    meta = chunk.to_chroma_metadata()

    # All top-level keys must be scalar (Chroma requirement)
    for v in meta.values():
        assert isinstance(v, (str, int, float, bool)), f"Non-scalar value: {v!r}"

    assert meta["modality"] == "table"
    assert meta["page_number"] == 3
    assert meta["scalar"] == 42
    # Nested dicts should be skipped
    assert "nested" not in meta


def test_document_chunk_image_metadata():
    chunk = DocumentChunk(
        content="An image",
        modality=Modality.IMAGE,
        image_base64="abc123==",
        image_mime_type="image/png",
    )
    meta = chunk.to_chroma_metadata()
    assert meta["has_image"] is True
    assert meta["image_base64"] == "abc123=="


def test_document_chunk_copy_preserves_id():
    chunk = DocumentChunk(content="Original")
    clone = chunk.model_copy(update={"content": "Modified"})
    assert clone.id == chunk.id
    assert clone.content == "Modified"

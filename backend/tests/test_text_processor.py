"""Tests for processors/text_processor.py"""

from models.document import DocumentChunk, Modality
from processors.text_processor import TextProcessor


def _make_chunk(text: str, modality: Modality = Modality.TEXT) -> DocumentChunk:
    return DocumentChunk(content=text, modality=modality)


def test_short_text_passes_through():
    processor = TextProcessor(chunk_size=500, chunk_overlap=50)
    chunk = _make_chunk("Short text that fits in one chunk.")
    result = processor.process([chunk])
    assert len(result) == 1
    assert result[0].content == "Short text that fits in one chunk."


def test_long_text_is_split():
    processor = TextProcessor(chunk_size=100, chunk_overlap=10)
    long_text = " ".join([f"Sentence number {i}." for i in range(50)])
    chunk = _make_chunk(long_text)
    result = processor.process([chunk])
    assert len(result) > 1
    for r in result:
        assert len(r.content) <= 120  # allow slight overlap


def test_image_chunk_passes_through_unchanged():
    processor = TextProcessor(chunk_size=50, chunk_overlap=5)
    img_chunk = _make_chunk("x" * 500, modality=Modality.IMAGE)
    result = processor.process([img_chunk])
    assert len(result) == 1
    assert result[0].modality == Modality.IMAGE


def test_sub_chunk_index_in_metadata():
    processor = TextProcessor(chunk_size=100, chunk_overlap=0)
    long_text = "A" * 400
    chunk = _make_chunk(long_text)
    result = processor.process([chunk])
    assert len(result) > 1
    indices = [r.metadata.get("sub_chunk_index") for r in result]
    assert indices[0] == 0
    assert indices[-1] == len(result) - 1


def test_mixed_modalities():
    processor = TextProcessor(chunk_size=50, chunk_overlap=0)
    chunks = [
        _make_chunk("A" * 200, Modality.TEXT),
        _make_chunk("B" * 10, Modality.IMAGE),
        _make_chunk("C" * 200, Modality.TABLE),
    ]
    result = processor.process(chunks)
    # IMAGE chunk must not be split
    image_chunks = [c for c in result if c.modality == Modality.IMAGE]
    assert len(image_chunks) == 1
    # TEXT and TABLE must be split
    text_chunks = [c for c in result if c.modality == Modality.TEXT]
    table_chunks = [c for c in result if c.modality == Modality.TABLE]
    assert len(text_chunks) > 1
    assert len(table_chunks) > 1

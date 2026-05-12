"""Tests for loaders/loader_factory.py"""

import pytest

from loaders.loader_factory import LoaderFactory
from loaders.pdf_loader import PDFLoader
from loaders.docx_loader import DOCXLoader
from loaders.pptx_loader import PPTXLoader
from loaders.image_loader import ImageLoader
from loaders.csv_loader import CSVLoader
from loaders.web_loader import WebLoader
from loaders.youtube_loader import YouTubeLoader
from models.document import SourceType


@pytest.mark.parametrize(
    "path,expected_cls",
    [
        ("/tmp/doc.pdf", PDFLoader),
        ("/tmp/report.docx", DOCXLoader),
        ("/tmp/slides.pptx", PPTXLoader),
        ("/tmp/photo.jpg", ImageLoader),
        ("/tmp/photo.PNG", ImageLoader),
        ("/tmp/data.csv", CSVLoader),
        ("/tmp/sheet.xlsx", CSVLoader),
    ],
)
def test_from_path_returns_correct_loader(path, expected_cls):
    loader = LoaderFactory.from_path(path)
    assert isinstance(loader, expected_cls)


def test_from_path_returns_none_for_txt():
    loader = LoaderFactory.from_path("/tmp/notes.txt")
    assert loader is None


def test_from_path_returns_none_for_unknown_ext():
    loader = LoaderFactory.from_path("/tmp/file.unknown")
    assert loader is None


def test_from_url_returns_web_loader():
    loader = LoaderFactory.from_url("https://example.com/page")
    assert isinstance(loader, WebLoader)


def test_from_url_returns_youtube_loader():
    loader = LoaderFactory.from_url("https://www.youtube.com/watch?v=abc123")
    assert isinstance(loader, YouTubeLoader)


def test_get_by_source_type():
    assert isinstance(LoaderFactory.get(SourceType.PDF), PDFLoader)
    assert isinstance(LoaderFactory.get(SourceType.WEB), WebLoader)


def test_get_raises_for_unknown_type():
    with pytest.raises(ValueError):
        LoaderFactory.get(SourceType.UNKNOWN)

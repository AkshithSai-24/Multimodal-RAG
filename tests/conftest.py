import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

# Use test-specific values so tests never touch production data or real APIs
os.environ.setdefault("CHROMA_PERSIST_DIR", "/tmp/chroma_test")
os.environ.setdefault("CHROMA_COLLECTION_NAME", "test_collection")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")
os.environ.setdefault("EMBEDDING_MODEL", "models/text-embedding-004")
os.environ.setdefault("EMBEDDING_TASK_TYPE", "retrieval_document")

from main import app
from core.vectorstore import VectorStoreManager


@pytest.fixture(scope="session")
def client():
    """Synchronous TestClient with the lifespan run."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def vs_manager():
    """Return a fresh VectorStoreManager for unit tests."""
    return VectorStoreManager()

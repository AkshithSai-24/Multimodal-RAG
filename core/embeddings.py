"""
Embedding setup — Google Generative AI Embeddings.

Uses ``langchain_google_genai.GoogleGenerativeAIEmbeddings`` which calls the
Google Gemini Embeddings API (``text-embedding-004`` by default).

Requires:
    GOOGLE_API_KEY  — obtain from https://aistudio.google.com/app/apikey
    EMBEDDING_MODEL — defaults to "models/text-embedding-004"

Supported task types (pass via EMBEDDING_TASK_TYPE env var):
    retrieval_document  (default for ingestion)
    retrieval_query     (default for queries)
    semantic_similarity
    classification
    clustering
"""

from functools import lru_cache
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from config.settings import settings


@lru_cache(maxsize=1)
def get_embeddings() :
    """
    Return a cached Google Generative AI embedding model.

    ``task_type="retrieval_document"`` is the recommended setting when
    the same embedder is used for both ingestion and retrieval; the
    Gemini API accepts both document and query vectors under this type.
    """
    
    return NVIDIAEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.NVIDIA_API_KEY,
        )

    """
    from langchain_openai import OpenAIEmbeddings
    from langchain_openrouter import ChatOpenRouter

    embeddings = OpenAIEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=settings.OPENROUTER_API_KEY,
    )
    returbn embeddings
    """

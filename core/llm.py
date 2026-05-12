"""
LLM / Vision-LLM initialisation via langchain_openrouter.

Both a plain text LLM and a vision-capable LLM are exposed.
The vision LLM is used during ingestion (image summarisation) and at
query time (multi-modal context building).
"""

from functools import lru_cache

from langchain_openrouter import ChatOpenRouter
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from config.settings import settings

# Extra headers recommended by OpenRouter docs
_EXTRA_HEADERS = {
    "HTTP-Referer": settings.APP_SITE_URL,
    "X-Title": settings.APP_NAME,
}


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenRouter:
    """Return a cached text-only LLM."""
    return ChatOpenRouter(
        model=settings.LLM_MODEL,
        openrouter_api_key=settings.OPENROUTER_API_KEY,
        default_headers=_EXTRA_HEADERS,
        temperature=0.2,
        max_tokens=2048,
    )


@lru_cache(maxsize=1)

def get_vision_llm():
    """
    Return a cached vision-capable LLM.

    This model receives both text and base64-encoded image blocks.
    Make sure VISION_MODEL in settings points to a model that supports
    the vision / multimodal message format (e.g. claude-3.5-sonnet,
    gpt-4o, llava, etc.).
    """

    return ChatNVIDIA(
            model=settings.VISION_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            default_headers=_EXTRA_HEADERS,
            temperature=0.1,
            max_tokens=1024,
        )



'''def get_vision_llm() -> ChatOpenRouter:
    """
    Return a cached vision-capable LLM.

    This model receives both text and base64-encoded image blocks.
    Make sure VISION_MODEL in settings points to a model that supports
    the vision / multimodal message format (e.g. claude-3.5-sonnet,
    gpt-4o, llava, etc.).
    """
    return ChatOpenRouter(
        model=settings.VISION_MODEL,
        openrouter_api_key=settings.OPENROUTER_API_KEY,
        default_headers=_EXTRA_HEADERS,
        temperature=0.1,
        max_tokens=1024,
    )'''

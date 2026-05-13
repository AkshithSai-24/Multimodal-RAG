"""
LLM / Vision-LLM initialisation via langchain_openrouter.

Both a plain text LLM and a vision-capable LLM are exposed.
The vision LLM is used during ingestion (image summarisation) and at
query time (multi-modal context building).
"""

from functools import lru_cache

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openrouter import ChatOpenRouter

from config.settings import settings

# OpenRouter attribution is handled by app_url + app_title.
# Do NOT pass default_headers to ChatOpenRouter.
# That field is not part of the current ChatOpenRouter API and causes the warning/error.
_OPENROUTER_ATTRIBUTION = {
    "app_url": settings.APP_SITE_URL,
    "app_title": settings.APP_NAME,
}


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenRouter:
    """Return a cached text-only LLM."""
    return ChatOpenRouter(
        model=settings.LLM_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        **_OPENROUTER_ATTRIBUTION,
        temperature=0.2,
        max_tokens=2048,
    )


@lru_cache(maxsize=1)
def get_vision_llm() -> ChatNVIDIA:
    """
    Return a cached vision-capable LLM.

    This model receives both text and base64-encoded image blocks.
    Make sure VISION_MODEL in settings points to a model that supports
    the vision / multimodal message format.
    """
    return ChatNVIDIA(
        model=settings.VISION_MODEL,
        api_key=settings.NVIDIA_API_KEY,
        default_headers={
            "HTTP-Referer": settings.APP_SITE_URL,
            "X-Title": settings.APP_NAME,
        },
        temperature=0.1,
        max_completion_tokens=1024,
    )
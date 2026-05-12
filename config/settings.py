"""
Central configuration — all values come from environment variables (or .env).
"""

from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", case_sensitive=False)

    # ── OpenRouter ────────────────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = "your-openrouter-api-key"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Models available on OpenRouter — change to any model slug you prefer
    LLM_MODEL: str = "openai/gpt-oss-20b:free"
    VISION_MODEL: str = "meta/llama-4-maverick-17b-128e-instruct"   # must support vision
    NVIDIA_API_KEY: str = "your-nvidia-api-key"
    # App meta headers forwarded to OpenRouter (recommended by their docs)
    APP_SITE_URL: str = "http://localhost:8000"
    APP_NAME: str = "MultiModal-RAG"

    # ── Google Generative AI (Embeddings) ─────────────────────────────────────
    # Get your key at: https://aistudio.google.com/app/apikey
    GOOGLE_API_KEY: str = "your-google-api-key"

    # Google embedding model — "models/text-embedding-004" is the latest (2024)
    # Alternatives: "models/embedding-001"
    # Full list: https://ai.google.dev/gemini-api/docs/models/gemini#text-embedding
    EMBEDDING_MODEL: str = "nvidia/llama-nemotron-embed-1b-v2"

    # Task type hint sent to the Gemini Embeddings API
    # Options: retrieval_document | retrieval_query | semantic_similarity |
    #          classification | clustering | fact_verification
    EMBEDDING_TASK_TYPE: str = "retrieval_document"

    # ── Chroma ────────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "multimodal_rag"

    # ── MCP servers ───────────────────────────────────────────────────────────
    GDRIVE_MCP_URL: str = "https://drivemcp.googleapis.com/mcp/v1"
    GDRIVE_ACCESS_TOKEN: str = ""   # OAuth2 access token for Google Drive MCP

    # ── FastAPI ───────────────────────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["*"]

    # ── Chunking ──────────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # ── Retrieval ─────────────────────────────────────────────────────────────
    TOP_K: int = 6                   # docs to retrieve per query
    MAX_IMAGE_DOCS: int = 3          # max image docs passed to vision LLM
    INCLUDE_IMAGES_IN_RESPONSE: bool = True

    # ── Temp / uploads ────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50


settings = Settings()



def reload_settings_from_env() -> Settings:
    """Reload the .env file and refresh the shared settings object."""
    load_dotenv(".env", override=True)
    fresh = Settings()
    for field, value in fresh.model_dump().items():
        setattr(settings, field, value)
    return settings

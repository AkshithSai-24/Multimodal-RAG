"""
MultiModal RAG Backend — FastAPI entry point.
Initialises the vector-store, wires CORS, and mounts all routers.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import config, health, ingest, query
from config.settings import settings
from core.vectorstore import VectorStoreManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    # ── Startup ──────────────────────────────────────────────────────────────
    vs_manager = VectorStoreManager()
    await vs_manager.initialize()
    app.state.vs_manager = vs_manager
    app.state.use_vision_model = True
    print("✅  Vector-store ready.")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("🛑  Shutting down MultiModal RAG backend.")


app = FastAPI(
    title="MultiModal RAG API",
    description=(
        "Production-ready Multi-modal Retrieval-Augmented Generation backend "
        "with MCP-powered data sources, Chroma vector DB, and OpenRouter LLMs."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(config.router, prefix="/config", tags=["Config"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )

"""
Configuration endpoints.

POST /config/env — upload a .env file and reload backend settings.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from config.settings import reload_settings_from_env
from core.embeddings import get_embeddings
from core.llm import get_llm, get_vision_llm
from core.vectorstore import init_vectorstore
import mcp.registry as mcp_registry

router = APIRouter()


def _extract_env_keys(content: str) -> list[str]:
    keys: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.append(key)
    return keys


@router.post("/env")
async def upload_env(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".env"):
        raise HTTPException(status_code=400, detail="Please upload a .env file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded .env file is empty.")

    decoded = content.decode("utf-8", errors="replace")
    Path(".env").write_text(decoded, encoding="utf-8")

    reload_settings_from_env()
    get_embeddings.cache_clear()
    get_llm.cache_clear()
    get_vision_llm.cache_clear()
    mcp_registry._registry = None

    request.app.state.vs_manager = await init_vectorstore()
    return {
        "status": "ok",
        "path": ".env",
        "keys": _extract_env_keys(decoded),
        "message": "Environment file uploaded and backend reloaded successfully.",
    }

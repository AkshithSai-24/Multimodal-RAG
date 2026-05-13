"""
File utility helpers used by the ingest routes.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

_ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff",
    ".csv", ".tsv", ".xlsx", ".xls",
    ".txt", ".md",
}

_MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def validate_upload(file: UploadFile) -> None:
    """Raise HTTPException if the file is not acceptable."""
    if not file.filename:
        raise HTTPException(400, "Uploaded file has no filename.")
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            415,
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )


async def save_upload_temp(file: UploadFile) -> str:
    """
    Save an UploadFile to a temporary path on disk.
    Returns the path string.  Caller is responsible for deleting it.
    """
    validate_upload(file)
    suffix = Path(file.filename or "upload").suffix or ".bin"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as out:
            total = 0
            while chunk := await file.read(65536):
                total += len(chunk)
                if total > _MAX_BYTES:
                    raise HTTPException(
                        413,
                        f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
                    )
                out.write(chunk)
    except HTTPException:
        os.unlink(tmp_path)
        raise
    except Exception as exc:
        os.unlink(tmp_path)
        raise HTTPException(500, f"Failed to save upload: {exc}") from exc

    log.info("Saved upload to %s (%d bytes)", tmp_path, total)
    return tmp_path


def file_sha256(path: str) -> str:
    """Return the SHA-256 hex digest of a file (for deduplication)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()

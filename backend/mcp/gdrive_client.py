"""
Google Drive MCP Client.

Uses the Google Drive MCP server (https://drivemcp.googleapis.com/mcp/v1)
to list and download files, then delegates to the appropriate loader.

Supports:
  • Google Docs   → exported as plain text
  • Google Sheets → exported as CSV
  • Google Slides → exported as plain text
  • Native files  (.pdf, .docx, .pptx, images, …) → downloaded and loaded
"""

from __future__ import annotations

import base64
import io
import os
import tempfile
from pathlib import Path
from typing import List, Optional

import httpx

from config.settings import settings
from loaders.loader_factory import LoaderFactory
from mcp.base_client import MCPHTTPClient
from models.document import DocumentChunk, Modality, SourceType


_GOOGLE_MIME_EXPORT: dict[str, tuple[str, str]] = {
    "application/vnd.google-apps.document": (
        "text/plain",
        ".txt",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "text/csv",
        ".csv",
    ),
    "application/vnd.google-apps.presentation": (
        "text/plain",
        ".txt",
    ),
}


class GDriveClient:
    """Load documents from Google Drive via the Drive MCP server."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        token = access_token or settings.GDRIVE_ACCESS_TOKEN
        self._mcp = MCPHTTPClient(
            server_url=settings.GDRIVE_MCP_URL,
            auth_token=token,
        )
        self._access_token = token

    # ── Public API ────────────────────────────────────────────────────────────

    async def load_file(self, file_id: str) -> List[DocumentChunk]:
        """
        Download and parse a single Google Drive file by its ID.
        Returns a list of raw DocumentChunks for further processing.
        """
        # 1. Get file metadata
        meta = await self._get_metadata(file_id)
        if not meta:
            raise RuntimeError(f"Could not retrieve metadata for Drive file {file_id}")

        name: str = meta.get("name", file_id)
        mime: str = meta.get("mimeType", "")

        # 2. Download content
        content_bytes, effective_ext = await self._download(file_id, mime)
        if not content_bytes:
            raise RuntimeError(f"Empty download for Drive file {file_id}")

        # 3. Write to temp file and load with the appropriate loader
        with tempfile.NamedTemporaryFile(
            suffix=effective_ext, delete=False
        ) as tmp:
            tmp.write(content_bytes)
            tmp_path = tmp.name

        try:
            loader = LoaderFactory.from_path(tmp_path)
            if loader is not None:
                chunks = await loader.load(tmp_path)
            else:
                # Plain text fallback
                text = content_bytes.decode("utf-8", errors="replace")
                chunks = [
                    DocumentChunk(
                        content=text,
                        modality=Modality.TEXT,
                        source_type=SourceType.GDRIVE,
                        source_id=file_id,
                        source_name=name,
                    )
                ]
        finally:
            os.unlink(tmp_path)

        # Patch source metadata
        for chunk in chunks:
            chunk.source_type = SourceType.GDRIVE
            chunk.source_id = file_id
            chunk.source_name = name

        return chunks

    async def list_files(self, folder_id: Optional[str] = None) -> list:
        """
        List files accessible to the authenticated user via the MCP server.
        Returns a list of {id, name, mimeType} dicts.
        """
        args = {}
        if folder_id:
            args["folderId"] = folder_id
        result = await self._mcp.call_tool("files.list", args)
        return result.get("files", []) if result else []

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_metadata(self, file_id: str) -> Optional[dict]:
        try:
            result = await self._mcp.call_tool(
                "files.get",
                {"fileId": file_id, "fields": "id,name,mimeType,size"},
            )
            return result
        except Exception as exc:
            print(f"[GDriveClient] metadata error: {exc}")
            return None

    async def _download(self, file_id: str, mime: str) -> tuple[bytes, str]:
        """
        Download the file bytes.  For Google-native types, exports to a
        compatible format first.
        """
        export_info = _GOOGLE_MIME_EXPORT.get(mime)

        if export_info:
            export_mime, ext = export_info
            url = (
                f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
                f"?mimeType={export_mime}"
            )
        else:
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            # Guess extension from MIME
            ext = self._ext_from_mime(mime)

        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with httpx.AsyncClient(timeout=60, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content, ext

    @staticmethod
    def _ext_from_mime(mime: str) -> str:
        table = {
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "text/plain": ".txt",
            "text/csv": ".csv",
        }
        return table.get(mime, ".bin")

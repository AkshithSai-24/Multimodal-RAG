"""
Web loader — scrapes pages using *requests* + *trafilatura* (main text) and
*BeautifulSoup* (images / metadata). No Playwright / browser dependency.

Supports optional shallow crawl (max_depth pages via same-domain hrefs).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import re
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from loaders.base_loader import BaseLoader
from models.document import DocumentChunk, Modality, SourceType


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MultiModalRAG/1.0; +https://github.com/your-org/mmrag)"
    )
}
_IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}


class WebLoader(BaseLoader):
    """Scrape one or more web pages and extract text + images."""

    def __init__(self, max_depth: int = 1, max_pages: int = 20, timeout: int = 15):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = timeout

    # ── Public API ────────────────────────────────────────────────────────────

    async def load(self, source: str, **kwargs) -> List[DocumentChunk]:
        max_depth = kwargs.get("max_depth", self.max_depth)
        visited: Set[str] = set()
        chunks: List[DocumentChunk] = []
        await self._crawl(source, source, 0, max_depth, visited, chunks)
        return chunks

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _crawl(
        self,
        root_url: str,
        current_url: str,
        depth: int,
        max_depth: int,
        visited: Set[str],
        chunks: List[DocumentChunk],
    ) -> None:
        if current_url in visited or len(visited) >= self.max_pages:
            return
        visited.add(current_url)

        html = await self._fetch_html(current_url)
        if not html:
            return

        # ── Extract text via trafilatura ──────────────────────────────────────
        text = trafilatura.extract(
            html,
            include_tables=True,
            include_images=False,
            no_fallback=False,
        )
        if text:
            chunks.append(
                DocumentChunk(
                    content=text,
                    modality=Modality.TEXT,
                    source_type=SourceType.WEB,
                    source_id=current_url,
                    source_name=self._domain(current_url),
                )
            )

        # ── Extract images ────────────────────────────────────────────────────
        soup = BeautifulSoup(html, "lxml")
        for img_tag in soup.find_all("img", src=True):
            img_url = urljoin(current_url, img_tag["src"])
            if not self._is_image_url(img_url):
                continue
            img_bytes = await self._fetch_bytes(img_url)
            if img_bytes and len(img_bytes) > 2048:  # skip tiny icons
                b64 = base64.b64encode(img_bytes).decode()
                alt_text = img_tag.get("alt", "")
                chunks.append(
                    DocumentChunk(
                        content=alt_text or f"Image from {current_url}",
                        modality=Modality.IMAGE,
                        source_type=SourceType.WEB,
                        source_id=img_url,
                        source_name=self._domain(current_url),
                        image_base64=b64,
                        image_mime_type=self._mime_for_url(img_url),
                        metadata={"page_url": current_url},
                    )
                )

        # ── Recurse same-domain links ─────────────────────────────────────────
        if depth < max_depth:
            root_domain = self._domain(root_url)
            for a_tag in soup.find_all("a", href=True):
                href = urljoin(current_url, a_tag["href"])
                href = href.split("#")[0]  # strip anchors
                if self._domain(href) == root_domain and href not in visited:
                    await self._crawl(root_url, href, depth + 1, max_depth, visited, chunks)

    async def _fetch_html(self, url: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(headers=_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:
            print(f"[WebLoader] Failed to fetch {url}: {exc}")
            return None

    async def _fetch_bytes(self, url: str) -> Optional[bytes]:
        try:
            async with httpx.AsyncClient(headers=_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception:
            return None

    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc

    @staticmethod
    def _is_image_url(url: str) -> bool:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in _IMG_EXTS)

    @staticmethod
    def _mime_for_url(url: str) -> str:
        path = urlparse(url).path.lower()
        if path.endswith(".png"):
            return "image/png"
        if path.endswith(".gif"):
            return "image/gif"
        if path.endswith(".webp"):
            return "image/webp"
        return "image/jpeg"

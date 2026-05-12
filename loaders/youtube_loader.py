"""
YouTube Loader — fetches auto-generated / manual captions via
*youtube_transcript_api* (no browser, no scraping).
"""

from __future__ import annotations

import re
from typing import List

from youtube_transcript_api import YouTubeTranscriptApi

from loaders.base_loader import BaseLoader
from models.document import DocumentChunk, Modality, SourceType


_WINDOW_SECONDS = 120    # Combine captions into 2-minute windows


def _extract_video_id(url_or_id: str) -> str:
    """Extract the YouTube video ID from various URL formats or bare ID."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url_or_id)
        if m:
            return m.group(1)
    # Assume it's already an ID
    return url_or_id.strip()


class YouTubeLoader(BaseLoader):
    """Transcribe YouTube videos via the Transcript API."""

    async def load(self, source: str, **kwargs) -> List[DocumentChunk]:
        video_id = _extract_video_id(source)
        chunks: List[DocumentChunk] = []

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as exc:
            raise RuntimeError(f"Could not fetch transcript for {video_id}: {exc}") from exc

        # Combine entries into time windows
        window_text: List[str] = []
        window_start = 0.0
        window_num = 1

        for entry in transcript:
            window_text.append(entry["text"])
            if entry["start"] - window_start >= _WINDOW_SECONDS:
                combined = " ".join(window_text).strip()
                if combined:
                    chunks.append(
                        DocumentChunk(
                            content=combined,
                            modality=Modality.TEXT,
                            source_type=SourceType.YOUTUBE,
                            source_id=f"https://youtu.be/{video_id}",
                            source_name=f"YouTube:{video_id}",
                            page_number=window_num,
                            metadata={
                                "window_start_sec": window_start,
                                "video_id": video_id,
                            },
                        )
                    )
                window_text = []
                window_start = entry["start"]
                window_num += 1

        # Flush remaining
        if window_text:
            combined = " ".join(window_text).strip()
            if combined:
                chunks.append(
                    DocumentChunk(
                        content=combined,
                        modality=Modality.TEXT,
                        source_type=SourceType.YOUTUBE,
                        source_id=f"https://youtu.be/{video_id}",
                        source_name=f"YouTube:{video_id}",
                        page_number=window_num,
                        metadata={"video_id": video_id},
                    )
                )

        return chunks

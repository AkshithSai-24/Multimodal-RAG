"""
Image Loader — reads an image file from disk and wraps it in a DocumentChunk.
The vision summary is filled in later by the multimodal_processor.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import List

from PIL import Image as PILImage
import io

from loaders.base_loader import BaseLoader
from models.document import DocumentChunk, Modality, SourceType

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
}
_MAX_DIM = 1568   # Resize large images to fit vision-model limits


class ImageLoader(BaseLoader):
    """Load a single image file."""

    async def load(self, source: str, **kwargs) -> List[DocumentChunk]:
        path = Path(source)
        ext = path.suffix.lower()
        mime = _MIME_MAP.get(ext, "image/jpeg")

        # Resize to keep within typical vision-model limits
        with PILImage.open(str(path)) as img:
            img = img.convert("RGB")
            if max(img.size) > _MAX_DIM:
                img.thumbnail((_MAX_DIM, _MAX_DIM), PILImage.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            img_bytes = buf.getvalue()

        b64 = base64.b64encode(img_bytes).decode()
        return [
            DocumentChunk(
                content=f"Image: {path.name}",
                modality=Modality.IMAGE,
                source_type=SourceType.IMAGE,
                source_id=str(path),
                source_name=path.name,
                image_base64=b64,
                image_mime_type="image/jpeg",
            )
        ]

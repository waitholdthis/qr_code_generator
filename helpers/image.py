from __future__ import annotations

import io
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image

MAX_REMOTE_IMAGE_BYTES = 20 * 1024 * 1024


def load_image(source: str | Path) -> Image.Image:
    """Load a local or HTTP(S) image and return a detached RGBA copy."""
    source_text = str(source)
    parsed = urlparse(source_text)
    if parsed.scheme in {"http", "https"}:
        return _load_remote_image(source_text)

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {source}")
    with Image.open(path) as img:
        return img.convert("RGBA")


def _load_remote_image(url: str) -> Image.Image:
    request = Request(url, headers={"User-Agent": "qr-code-generator/0.1"})
    with urlopen(request, timeout=15) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_REMOTE_IMAGE_BYTES:
            raise ValueError("Remote image is larger than 20 MB")

        data = response.read(MAX_REMOTE_IMAGE_BYTES + 1)
        if len(data) > MAX_REMOTE_IMAGE_BYTES:
            raise ValueError("Remote image is larger than 20 MB")

    with Image.open(io.BytesIO(data)) as img:
        return img.convert("RGBA")

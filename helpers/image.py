from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image


def load_image(source: str | Path) -> Image.Image:
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {source}")
    with Image.open(path) as img:
        return img.convert("RGBA")

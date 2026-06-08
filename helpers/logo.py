from __future__ import annotations

from PIL import Image


def center_logo(*, qr_img: Image.Image, logo: Image.Image, scale: float = 0.2) -> Image.Image:
    base = qr_img.convert("RGBA")
    logo = logo.convert("RGBA")
    w, h = base.size
    shorter = min(w, h)
    new_size = max(1, int(shorter * scale))
    logo = logo.resize((new_size, new_size), Image.Resampling.LANCZOS)
    x = (w - new_size) // 2
    y = (h - new_size) // 2
    base.alpha_composite(logo, (x, y))
    return base.convert("RGB")

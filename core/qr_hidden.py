from __future__ import annotations

from typing import Tuple

import qrcode
from PIL import Image


def qr_from_hidden(data: str, logo_path: str, output_path: str, qr_size: int = 256, scale: float = 0.18, alpha: int = 180) -> str:
    base = Image.open(logo_path).convert("RGBA")
    qr = _make_qr(data, size=qr_size)
    qr = _apply_alpha(qr, alpha)
    qr = _resize_to_scale(qr, base.size, scale=scale)
    x, y = _center(qr, base.size)

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay.paste(qr, (x, y), qr)

    out = Image.alpha_composite(base, overlay)
    out = out.convert("RGB")
    out.save(output_path)
    return output_path


def _make_qr(data: str, size: int = 256) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    img = img.resize((size, size), Image.Resampling.NEAREST)
    return img


def _apply_alpha(img: Image.Image, alpha: int) -> Image.Image:
    r, g, b, _ = img.split()
    a = Image.new("L", img.size, int(alpha))
    return Image.merge("RGBA", (r, g, b, a))


def _resize_to_scale(img: Image.Image, canvas_size, scale: float) -> Image.Image:
    w, h = canvas_size
    shorter = min(w, h)
    new = max(24, int(shorter * scale))
    return img.resize((new, new), Image.Resampling.LANCZOS)


def _center(img: Image.Image, canvas_size) -> Tuple[int, int]:
    w, h = canvas_size
    iw, ih = img.size
    x = (w - iw) // 2
    y = (h - ih) // 2
    return (x, y)

from __future__ import annotations

from typing import Sequence, Tuple

import qrcode
from PIL import Image


def qr_from_hidden(
    data: str,
    logo_path: str,
    output_path: str,
    qr_size: int = 256,
    scale: float = 0.40,
    alpha: int = 180,
    strength: int = 35,
    finder_boost: float = 1.85,
    min_short_side: int = 768,
    placement: str = "auto",
) -> str:
    """Blend a phone-scannable QR into image luminance while preserving composition."""
    base = Image.open(logo_path).convert("RGB")
    base = _ensure_min_short_side(base, min_short_side)
    out = _blend_luminance_qr(
        base=base,
        matrix=_make_qr_matrix(data),
        scale=scale,
        strength=strength,
        finder_boost=finder_boost,
        placement=placement,
    )
    out.save(output_path)
    return output_path


def _ensure_min_short_side(img: Image.Image, min_short_side: int) -> Image.Image:
    if min_short_side <= 0:
        return img
    w, h = img.size
    short_side = min(w, h)
    if short_side >= min_short_side:
        return img
    ratio = min_short_side / short_side
    size = (int(w * ratio), int(h * ratio))
    return img.resize(size, Image.Resampling.LANCZOS)


def _blend_luminance_qr(
    *,
    base: Image.Image,
    matrix: Sequence[Sequence[bool]],
    scale: float,
    strength: int,
    finder_boost: float,
    placement: str,
) -> Image.Image:
    matrix_size = len(matrix)
    w, h = base.size
    target = max(1, int(min(w, h) * max(0.1, min(scale, 0.95))))
    module_px = max(2, target // matrix_size)
    qr_px = module_px * matrix_size
    x0, y0 = _placement_origin(base, (qr_px, qr_px), placement)

    out = base.copy()
    pixels = out.load()
    opacity = max(0.05, min(strength / 100, 1.0))

    for my, row in enumerate(matrix):
        for mx, dark in enumerate(row):
            module_opacity = opacity
            if _is_finder_region(mx, my, matrix_size):
                module_opacity = min(1.0, opacity * finder_boost)
            target_luma = 0 if dark else 255

            for py in range(my * module_px, (my + 1) * module_px):
                y = y0 + py
                if y < 0 or y >= h:
                    continue
                for px in range(mx * module_px, (mx + 1) * module_px):
                    x = x0 + px
                    if x < 0 or x >= w:
                        continue
                    r, g, b = pixels[x, y]
                    pixels[x, y] = (
                        _mix_channel(r, target_luma, module_opacity),
                        _mix_channel(g, target_luma, module_opacity),
                        _mix_channel(b, target_luma, module_opacity),
                    )

    return out


def _make_qr_matrix(data: str) -> list[list[bool]]:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=1,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.get_matrix()


def _center_size(size: tuple[int, int], canvas_size: tuple[int, int]) -> Tuple[int, int]:
    w, h = canvas_size
    iw, ih = size
    x = (w - iw) // 2
    y = (h - ih) // 2
    return (x, y)


def _placement_origin(base: Image.Image, size: tuple[int, int], placement: str) -> Tuple[int, int]:
    placement = placement.lower()
    if placement != "auto":
        return _fixed_placement_origin(size, base.size, placement)

    w, h = base.size
    qw, qh = size
    if qw >= w or qh >= h:
        return _center_size(size, base.size)

    gray = base.convert("L").resize((max(1, w // 12), max(1, h // 12)), Image.Resampling.BILINEAR)
    sw, sh = gray.size
    sqw = max(1, int(qw / w * sw))
    sqh = max(1, int(qh / h * sh))
    step_x = max(1, sqw // 4)
    step_y = max(1, sqh // 4)

    best_score: float | None = None
    best = (0, 0)
    for sy in range(0, max(1, sh - sqh + 1), step_y):
        for sx in range(0, max(1, sw - sqw + 1), step_x):
            score = _region_score(gray, sx, sy, sqw, sqh)
            if best_score is None or score < best_score:
                best_score = score
                best = (sx, sy)

    return (int(best[0] / sw * w), int(best[1] / sh * h))


def _fixed_placement_origin(size: tuple[int, int], canvas_size: tuple[int, int], placement: str) -> Tuple[int, int]:
    qw, qh = size
    w, h = canvas_size
    x = (w - qw) // 2
    y = (h - qh) // 2
    if "left" in placement:
        x = 0
    elif "right" in placement:
        x = w - qw
    if "top" in placement:
        y = 0
    elif "bottom" in placement:
        y = h - qh
    return (max(0, x), max(0, y))


def _region_score(gray: Image.Image, x0: int, y0: int, w: int, h: int) -> float:
    pixels = gray.load()
    total = 0
    total_sq = 0
    edges = 0
    count = 0
    for y in range(y0, min(gray.height, y0 + h)):
        for x in range(x0, min(gray.width, x0 + w)):
            value = pixels[x, y]
            total += value
            total_sq += value * value
            count += 1
            if x > x0:
                edges += abs(value - pixels[x - 1, y])
            if y > y0:
                edges += abs(value - pixels[x, y - 1])
    if count == 0:
        return 0
    mean = total / count
    variance = total_sq / count - mean * mean
    return variance + edges / count


def _is_finder_region(x: int, y: int, matrix_size: int) -> bool:
    finder = 11
    return (
        (x < finder and y < finder)
        or (x >= matrix_size - finder and y < finder)
        or (x < finder and y >= matrix_size - finder)
    )


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def _mix_channel(value: int, target: int, opacity: float) -> int:
    return _clamp(int(value * (1 - opacity) + target * opacity))

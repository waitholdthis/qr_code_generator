from __future__ import annotations

import base64
import hashlib
from typing import Iterable, Tuple

import qrcode
from PIL import Image, ImageDraw


def qr_module_offsets(matrix_width: int) -> Iterable[Tuple[int, int]]:
    return [(r, c) for r in range(matrix_width) for c in range(matrix_width)]


def qr_from_data(payload: str | bytes, output_size: int = 2048) -> Image.Image:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(base64.b64encode(payload).decode("ascii"))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    if output_size:
        img = img.resize((output_size, output_size), Image.Resampling.NEAREST)
    return img


def qr_from_image(img: Image.Image, max_size: int = 16, output_size: int | None = None) -> Image.Image:
    src = img.convert("RGB")

    grid = max(4, int(max_size))
    src = src.resize((grid, grid), Image.Resampling.BILINEAR)

    palette = _build_palette(src)
    map_ids = _map_to_ids(src, palette)

    cube = list(map_ids)

    preview = _encode_cube(cube, grid)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(preview)
    try:
        qr.make(fit=True)
    except Exception:
        fallback = hashlib.sha256(preview).hexdigest().encode("ascii")
        qr = qrcode.QRCode(
            version=10,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(fallback)
        qr.make(fit=False)

    matrix = qr.get_matrix()
    matrix_size = qr.modules_count or len(matrix)
    qr_pixels = _matrix_to_pixels(matrix, matrix_size)

    size = next_power_of_two(grid) * 8 + 17
    final = Image.new("RGB", (size, size), "white")
    for r in range(min(size, len(qr_pixels))):
        for c in range(min(size, len(qr_pixels[0]))):
            if qr_pixels[r][c]:
                final.putpixel((c, r), (0, 0, 0))

    if output_size:
        final = final.resize((output_size, output_size), Image.Resampling.NEAREST)
    return final


def qr_from_image_mosaic(
    img: Image.Image,
    data: str,
    output_size: int = 1600,
    error_correction: int = qrcode.constants.ERROR_CORRECT_H,
) -> Image.Image:
    """Render a scan-ready QR whose modules are colored from the source image."""
    src = _square_cover(img.convert("RGB"))

    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=1,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    matrix_size = len(matrix)
    module_px = max(4, output_size // matrix_size)
    size = matrix_size * module_px
    sampled = src.resize((matrix_size, matrix_size), Image.Resampling.BILINEAR)
    out = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(out)

    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            color = sampled.getpixel((x, y))
            if _is_finder_region(x, y, matrix_size):
                color = _force_luma(color, 36 if dark else 238)
            else:
                color = _force_luma(color, 58 if dark else 222)

            x0 = x * module_px
            y0 = y * module_px
            draw.rectangle((x0, y0, x0 + module_px - 1, y0 + module_px - 1), fill=color)

    return out


def qr_from_colored_photo_overlay(
    img: Image.Image,
    data: str,
    color: str = "#00e5ff",
    scale: float = 0.62,
    opacity: float = 0.82,
    placement: str = "center",
    min_short_side: int = 768,
    error_correction: int = qrcode.constants.ERROR_CORRECT_H,
) -> Image.Image:
    """Keep the photo intact and overlay visible colored QR modules."""
    base = _ensure_min_short_side(img.convert("RGB"), min_short_side)
    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=1,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    matrix_size = len(matrix)
    w, h = base.size
    target = max(1, int(min(w, h) * max(0.15, min(scale, 0.95))))
    module_px = max(2, target // matrix_size)
    qr_px = module_px * matrix_size
    x0, y0 = _placement_origin((qr_px, qr_px), base.size, placement)

    out = base.convert("RGBA")
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    fill = _hex_to_rgb(color) + (int(255 * max(0.05, min(opacity, 1.0))),)
    finder_fill = _hex_to_rgb(color) + (int(255 * max(0.05, min(opacity * 1.18, 1.0))),)

    for my, row in enumerate(matrix):
        for mx, dark in enumerate(row):
            if not dark:
                continue
            left = x0 + mx * module_px
            top = y0 + my * module_px
            right = left + module_px - 1
            bottom = top + module_px - 1
            module_fill = finder_fill if _is_finder_region(mx, my, matrix_size) else fill
            draw.rectangle((left, top, right, bottom), fill=module_fill)

    return Image.alpha_composite(out, overlay).convert("RGB")


def _build_palette(src: Image.Image) -> list[tuple[int, int, int]]:
    raw = sorted(set(src.getdata()))
    keep: list[tuple[int, int, int]] = []
    for color in raw:
        if not any(_dist(color, existing) < 48 for existing in keep):
            keep.append(color)
        if len(keep) >= 16:
            break
    if not keep:
        keep.append((0, 0, 0))
    return keep


def _dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _map_to_ids(src: Image.Image, palette: list[tuple[int, int, int]]) -> list[int]:
    return [min(range(len(palette)), key=lambda i: _dist(px, palette[i])) for px in list(src.getdata())]


def _encode_cube(cube: list[int], grid: int) -> bytes:
    nibbles = ["".join(f"{id & 0x0F:X}" for id in cube[i * grid:(i + 1) * grid]) for i in range(grid)]
    body = ";".join(nibbles)
    return f"GRID={grid};PAL={_nibble_list(_median_palette(cube))};DATA={body}".encode("ascii")


def _median_palette(cube: list[int]) -> tuple[int, int, int, int]:
    unique = sorted(set(cube))[:16]
    if len(unique) < 4:
        unique = (unique + unique + unique + unique)[:4]
    return tuple(unique)


def _nibble_list(items: tuple[int, ...]) -> str:
    return "".join(f"{x:X}" for x in items)


def _matrix_to_pixels(matrix, matrix_size: int):
    return [[matrix[r][c] for c in range(matrix_size)] for r in range(matrix_size)]


def next_power_of_two(n: int) -> int:
    power = 1
    while power < n:
        power <<= 1
    return power


def _square_cover(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def _ensure_min_short_side(img: Image.Image, min_short_side: int) -> Image.Image:
    if min_short_side <= 0:
        return img
    w, h = img.size
    short_side = min(w, h)
    if short_side >= min_short_side:
        return img
    ratio = min_short_side / short_side
    return img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)


def _placement_origin(size: tuple[int, int], canvas_size: tuple[int, int], placement: str) -> tuple[int, int]:
    qw, qh = size
    w, h = canvas_size
    placement = placement.lower()
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


def _is_finder_region(x: int, y: int, matrix_size: int) -> bool:
    finder = 11
    return (
        (x < finder and y < finder)
        or (x >= matrix_size - finder and y < finder)
        or (x < finder and y >= matrix_size - finder)
    )


def _force_luma(color: tuple[int, int, int], target_luma: int) -> tuple[int, int, int]:
    current = _luma(color)
    if target_luma >= current:
        factor = (target_luma - current) / max(1, 255 - current)
        return tuple(_clamp(int(channel + (255 - channel) * factor)) for channel in color)
    factor = target_luma / max(1, current)
    return tuple(_clamp(int(channel * factor)) for channel in color)


def _luma(color: tuple[int, int, int]) -> int:
    r, g, b = color
    return int(0.299 * r + 0.587 * g + 0.114 * b)


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    if len(value) != 6:
        raise ValueError("QR color must be a 3- or 6-digit hex color")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

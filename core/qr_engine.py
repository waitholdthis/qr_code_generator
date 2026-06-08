from __future__ import annotations

import base64
import hashlib
from typing import Iterable, Tuple

import qrcode
from PIL import Image


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

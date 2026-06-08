from __future__ import annotations

from typing import Optional

from PIL import Image

from core.qr_engine import qr_from_data, qr_from_image
from helpers.image import load_image  # noqa: F401  (kept for compatibility with CLI usage patterns)


class QRCodeGeneratorApp:
    def __init__(self, *, error_correction: str = "H", foreground: str = "black", background: str = "white") -> None:
        if error_correction not in {"L", "M", "Q", "H"}:
            raise ValueError("error_correction must be one of L, M, Q, H")
        self.error_correction = error_correction
        self.foreground = foreground
        self.background = background

    def qr_from_image_path(self, image_path: str, output_path: str, max_size: int = 16) -> str:
        with Image.open(image_path) as img:
            qr_image = qr_from_image(img, max_size=max_size)
            qr_image.save(output_path)
        return output_path

    def qr_from_text(self, text: str, output_path: str, size: Optional[int] = None) -> str:
        qr_image = qr_from_data(text)
        if size is not None:
            qr_image = qr_image.resize((size, size), Image.Resampling.LANCZOS)
        qr_image.save(output_path)
        return output_path

    def styled_qr_from_text(self, text: str, output_path: str, qr_size: int = 1000, logo_path: Optional[str] = None, logo_scale: float = 0.2) -> str:
        base_qr = qr_from_data(text, output_size=qr_size)

        if logo_path:
            logo_image = Image.open(logo_path)
            from helpers.logo import center_logo
            base_qr = center_logo(qr_img=base_qr, logo=logo_image, scale=logo_scale)

        base_qr.save(output_path)
        return output_path
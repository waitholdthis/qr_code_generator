from __future__ import annotations

import functools
import http.server
import io
import socketserver
import threading
from pathlib import Path

from click.testing import CliRunner
from PIL import Image

from app import app
from cli import main
from core import qr_engine
from core.qr_engine import qr_from_colored_photo_overlay, qr_from_data, qr_from_image_mosaic
from helpers.image import load_image


FIXTURES = Path(__file__).parent / "fixtures"


def test_load_image_from_path_returns_rgba() -> None:
    img = load_image(FIXTURES / "logo.png")

    assert img.mode == "RGBA"
    assert img.width > 0
    assert img.height > 0


def test_load_image_from_http_url(tmp_path: Path) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FIXTURES))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            img = load_image(f"http://127.0.0.1:{server.server_address[1]}/logo.png")
        finally:
            server.shutdown()
            thread.join(timeout=5)

    assert img.mode == "RGBA"
    assert img.size[0] > 0


def test_qr_from_data_encodes_text_directly(monkeypatch) -> None:
    captured: list[str | bytes] = []
    original_add_data = qr_engine.qrcode.QRCode.add_data

    def spy_add_data(self, data, *args, **kwargs):
        captured.append(data)
        return original_add_data(self, data, *args, **kwargs)

    monkeypatch.setattr(qr_engine.qrcode.QRCode, "add_data", spy_add_data)

    qr_from_data("https://tootiedesigns.com", output_size=256)

    assert captured == [b"https://tootiedesigns.com"]


def test_qr_from_data_and_visual_modes_generate_images() -> None:
    source = Image.open(FIXTURES / "logo.png")

    data_qr = qr_from_data("https://tootiedesigns.com", output_size=256)
    mosaic_qr = qr_from_image_mosaic(source, data="https://tootiedesigns.com", output_size=512)
    color_qr = qr_from_colored_photo_overlay(source, data="https://tootiedesigns.com")

    assert data_qr.size == (256, 256)
    assert mosaic_qr.width == mosaic_qr.height
    assert color_qr.width >= source.width or color_qr.height >= source.height


def test_cli_color_mode_writes_png(tmp_path: Path) -> None:
    out = tmp_path / "color.png"
    result = CliRunner().invoke(
        main,
        [
            "--mode",
            "color",
            "--input",
            str(FIXTURES / "logo.png"),
            "--text",
            "https://tootiedesigns.com",
            "--output",
            str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert out.exists()
    with Image.open(out) as generated:
        assert generated.format == "PNG"


def test_flask_rejects_bad_numeric_input_without_500() -> None:
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.post(
            "/",
            data={
                "picture": (io.BytesIO((FIXTURES / "logo.png").read_bytes()), "logo.png"),
                "mode": "color",
                "text": "https://tootiedesigns.com",
                "scale": "not-a-number",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    assert b"Scale must be a number" in response.data


def test_flask_generates_color_mode_preview() -> None:
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.post(
            "/",
            data={
                "picture": (io.BytesIO((FIXTURES / "logo.png").read_bytes()), "logo.png"),
                "mode": "color",
                "text": "https://tootiedesigns.com",
                "scale": "0.40",
                "opacity": "0.82",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    assert b"/files/qr_" in response.data


def test_flask_file_route_blocks_path_traversal() -> None:
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/files/../app.py")

    assert response.status_code == 404

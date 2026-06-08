from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask import Flask, flash, redirect, render_template_string, request, send_file
from werkzeug.utils import secure_filename

import helpers.image as image_helper
import core.qr_hidden as qr_hidden
from core.qr_engine import qr_from_data, qr_from_image
from helpers.logo import center_logo

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
app.secret_key = os.urandom(16).hex()

OUT_DIR = Path("uploads").resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

HTML = """\
<!doctype html>
<title>QR from image</title>
<h1>Upload a picture to turn into a QR code</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=picture required />
  <select name=mode>
    <option value=subtle selected>Subtle Camera QR</option>
    <option value=data>Data QR</option>
    <option value=brand>Brand QR</option>
  </select>
  <input type=text name=text placeholder='Text or URL to scan' />
  <br/>
  <label>Max short-side (data mode): <input type=number name=max_size value=16 min=4 max=64 /></label>
  <br/>
  <label>QR coverage: <input type=number name=scale value=0.40 min=0.35 max=0.95 step=0.01 /></label>
  <label>Scan strength: <input type=number name=strength value=35 min=8 max=100 /></label>
  <label>Min short side: <input type=number name=min_short_side value=768 min=256 max=2400 /></label>
  <select name=placement>
    <option value=auto selected>Auto placement</option>
    <option value=center>Center</option>
    <option value=top-left>Top left</option>
    <option value=top-right>Top right</option>
    <option value=bottom-left>Bottom left</option>
    <option value=bottom-right>Bottom right</option>
  </select>
  <br/>
  <button type=submit>Generate</button>
</form>
{% if error %}
<p style="color:red">{{ error }}</p>
{% endif %}
{% if qr_path %}
<p>QR code saved: <a href="{{ qr_path }}">{{ qr_path }}</a></p>
<p><img src="{{ qr_path }}" style="max-width: 600px" /></p>
<p><a href="{{ qr_path }}" download>Download PNG</a></p>
{% endif %}
"""

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index() -> str | bytes:
    error = None
    qr_path = None

    if request.method == "POST":
        if "picture" not in request.files:
            error = "Missing picture file"
        else:
            file = request.files["picture"]
            mode = request.form.get("mode", "data")
            max_size = int(request.form.get("max_size", 16) or 16)
            scale = float(request.form.get("scale", 0.40) or 0.40)
            strength = int(request.form.get("strength", 35) or 35)
            min_short_side = int(request.form.get("min_short_side", 768) or 768)
            placement = request.form.get("placement", "auto")
            text = (request.form.get("text") or "").strip()

            if file.filename == "":
                error = "No file selected"
            elif not allowed_file(file.filename):
                error = "Unsupported file type"
            else:
                suffix = Path(secure_filename(file.filename)).suffix.lower() or ".bin"
                src_path = OUT_DIR / f"src_{next_stamp()}{suffix}"
                out_path = OUT_DIR / f"qr_{next_stamp()}.png"
                file.save(str(src_path))

                try:
                    uploaded_img = image_helper.load_image(src_path)
                    if mode == "brand":
                        if not text:
                            raise ValueError("Text or URL is required for brand mode")
                        qr_img = qr_from_data(text, output_size=2048)
                        qr_img = center_logo(qr_img=qr_img, logo=uploaded_img)
                    elif mode == "subtle":
                        if not text:
                            raise ValueError("Text or URL is required for subtle camera QR mode")
                        qr_hidden.qr_from_hidden(
                            data=text,
                            logo_path=str(src_path),
                            output_path=str(out_path),
                            scale=scale,
                            strength=strength,
                            min_short_side=min_short_side,
                            placement=placement,
                        )
                        qr_path = f"/files/{out_path.name}"
                    else:
                        qr_img = qr_from_image(uploaded_img, max_size=max_size)
                    if mode != "subtle":
                        qr_img.save(str(out_path))
                        qr_path = f"/files/{out_path.name}"
                except Exception as exc:  # pragma: no cover - defensive guard
                    error = f"Generation failed: {exc}"
                finally:
                    if src_path.exists():
                        src_path.unlink()

    tmpl = render_template_string(
        HTML, error=error, qr_path=qr_path
    )
    return tmpl


@app.route("/files/<name>")
def serve(name: str) -> bytes:
    path = OUT_DIR / name
    if not path.exists():
        return "Not found", 404
    return send_file(path, mimetype="image/png")


def next_stamp() -> int:
    from time import time_ns

    return int(time_ns() / 1_000_000)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False)

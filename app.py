from __future__ import annotations

import os
from pathlib import Path

from flask import render_template_string, request, send_file
from flask import Flask
from werkzeug.utils import secure_filename

import helpers.image as image_helper
import core.qr_hidden as qr_hidden
from core.qr_engine import qr_from_colored_photo_overlay, qr_from_data, qr_from_image, qr_from_image_mosaic
from helpers.logo import center_logo

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
app.secret_key = os.urandom(16).hex()

OUT_DIR = Path("uploads").resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

HTML = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cinematic QR Studio</title>
  <style>
    :root {
      color-scheme: dark;
      --ink: #f7f2e8;
      --muted: #b8b1a4;
      --panel: rgba(16, 18, 19, 0.86);
      --panel-strong: rgba(9, 10, 11, 0.94);
      --line: rgba(247, 242, 232, 0.18);
      --gold: #d8b45c;
      --cyan: #79cbd3;
      --red: #f26d5b;
      --field: #111417;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(115deg, rgba(4, 6, 8, 0.96), rgba(13, 20, 22, 0.9) 48%, rgba(28, 22, 12, 0.82)),
        repeating-linear-gradient(90deg, rgba(255,255,255,0.025) 0, rgba(255,255,255,0.025) 1px, transparent 1px, transparent 90px),
        #090b0c;
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }

    .shell {
      width: min(1320px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 0 22px;
      border-bottom: 1px solid var(--line);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .mark {
      display: grid;
      place-items: center;
      width: 40px;
      height: 40px;
      border: 1px solid var(--line);
      background: #111417;
      box-shadow: inset 0 0 0 6px #090b0c;
    }

    .mark::before {
      content: "";
      width: 14px;
      height: 14px;
      border: 4px solid var(--gold);
    }

    .brand h1 {
      margin: 0;
      font-size: clamp(1.2rem, 2vw, 1.9rem);
      font-weight: 760;
      line-height: 1.05;
    }

    .brand p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      color: var(--muted);
      background: rgba(247, 242, 232, 0.05);
      white-space: nowrap;
      font-size: 0.85rem;
    }

    .status-pill::before {
      content: "";
      width: 8px;
      height: 8px;
      background: var(--cyan);
      box-shadow: 0 0 18px var(--cyan);
    }

    .workspace {
      display: grid;
      grid-template-columns: minmax(330px, 430px) 1fr;
      gap: 22px;
      padding-top: 26px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }

    .controls {
      position: sticky;
      top: 18px;
      padding: 20px;
    }

    .panel-title {
      margin: 0 0 14px;
      font-size: 0.86rem;
      color: var(--gold);
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }

    .control-grid {
      display: grid;
      gap: 14px;
    }

    label {
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 0.84rem;
    }

    label span {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }

    .hint {
      color: rgba(247, 242, 232, 0.52);
      font-size: 0.76rem;
    }

    input,
    select,
    button {
      font: inherit;
      letter-spacing: 0;
    }

    input[type="file"],
    input[type="text"],
    input[type="number"],
    select {
      width: 100%;
      min-height: 44px;
      color: var(--ink);
      background: var(--field);
      border: 1px solid rgba(247, 242, 232, 0.16);
      padding: 10px 12px;
      outline: none;
    }

    input[type="file"] {
      padding: 8px;
    }

    input:focus,
    select:focus {
      border-color: var(--cyan);
      box-shadow: 0 0 0 3px rgba(121, 203, 211, 0.18);
    }

    .inline-fields {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .generate {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      width: 100%;
      min-height: 50px;
      margin-top: 4px;
      border: 0;
      color: #101010;
      background: var(--gold);
      font-weight: 800;
      cursor: pointer;
    }

    .generate:hover {
      filter: brightness(1.08);
    }

    .generate::before {
      content: "";
      width: 14px;
      height: 14px;
      border: 3px solid #101010;
      box-shadow: inset 0 0 0 3px var(--gold);
      background: #101010;
    }

    .error {
      margin: 14px 0 0;
      padding: 12px;
      color: #ffece8;
      border: 1px solid rgba(242, 109, 91, 0.5);
      background: rgba(242, 109, 91, 0.12);
    }

    .stage {
      min-height: 690px;
      display: grid;
      grid-template-rows: auto 1fr auto;
      overflow: hidden;
    }

    .stage-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-strong);
    }

    .stage-header h2 {
      margin: 0;
      font-size: clamp(1.5rem, 3vw, 3.2rem);
      line-height: 0.95;
      font-weight: 820;
    }

    .stage-header p {
      margin: 8px 0 0;
      color: var(--muted);
      max-width: 58ch;
    }

    .mode-badge {
      color: var(--cyan);
      border: 1px solid rgba(121, 203, 211, 0.34);
      padding: 9px 11px;
      background: rgba(121, 203, 211, 0.08);
      white-space: nowrap;
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .preview {
      display: grid;
      place-items: center;
      min-height: 420px;
      padding: 28px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.04), transparent 22%),
        repeating-linear-gradient(0deg, rgba(247,242,232,0.04) 0, rgba(247,242,232,0.04) 1px, transparent 1px, transparent 22px),
        #0b0d0f;
    }

    .preview-frame {
      width: 100%;
      min-height: 360px;
      display: grid;
      place-items: center;
      border: 1px solid rgba(247, 242, 232, 0.16);
      background: rgba(0, 0, 0, 0.25);
      padding: 18px;
    }

    .preview img {
      display: block;
      max-width: 100%;
      max-height: 600px;
      object-fit: contain;
      box-shadow: 0 20px 70px rgba(0, 0, 0, 0.55);
    }

    .empty-state {
      display: grid;
      place-items: center;
      gap: 16px;
      max-width: 520px;
      text-align: center;
      color: var(--muted);
    }

    .scanner-icon {
      width: 120px;
      height: 120px;
      border: 1px solid rgba(216, 180, 92, 0.55);
      position: relative;
      background:
        linear-gradient(90deg, transparent 45%, rgba(121, 203, 211, 0.22), transparent 55%),
        #111417;
    }

    .scanner-icon::before,
    .scanner-icon::after {
      content: "";
      position: absolute;
      inset: 18px;
      border: 8px solid var(--gold);
    }

    .scanner-icon::after {
      inset: 42px;
      border-color: rgba(247, 242, 232, 0.75);
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
      padding: 16px 20px;
      border-top: 1px solid var(--line);
      background: var(--panel-strong);
    }

    .action-link {
      color: var(--ink);
      border: 1px solid var(--line);
      padding: 10px 12px;
      text-decoration: none;
      background: rgba(247, 242, 232, 0.06);
    }

    .action-link.primary {
      color: #111;
      background: var(--cyan);
      border-color: var(--cyan);
      font-weight: 800;
    }

    .explain {
      margin-top: 22px;
      padding: 20px;
    }

    .explain-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .explain-item {
      min-height: 116px;
      padding: 14px;
      border: 1px solid rgba(247, 242, 232, 0.13);
      background: rgba(247, 242, 232, 0.045);
    }

    .explain-item h3 {
      margin: 0 0 7px;
      font-size: 0.93rem;
    }

    .explain-item p {
      margin: 0;
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.45;
    }

    @media (max-width: 980px) {
      .workspace,
      .explain-grid {
        grid-template-columns: 1fr;
      }

      .controls {
        position: static;
      }

      .stage {
        min-height: auto;
      }
    }

    @media (max-width: 620px) {
      .shell {
        width: min(100vw - 20px, 1320px);
        padding: 12px 0;
      }

      .topbar,
      .stage-header,
      .actions {
        align-items: flex-start;
        flex-direction: column;
      }

      .inline-fields {
        grid-template-columns: 1fr;
      }

      .preview {
        padding: 12px;
      }

      .preview-frame {
        min-height: 300px;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="mark" aria-hidden="true"></div>
        <div>
          <h1>Cinematic QR Studio</h1>
          <p>Blend scan-ready QR signals into polished image exports.</p>
        </div>
      </div>
      <div class="status-pill">Phone-camera optimized</div>
    </header>

    <section class="workspace">
      <form class="panel controls" method="post" enctype="multipart/form-data">
        <p class="panel-title">Build</p>
        <div class="control-grid">
          <label>
            <span>Picture <small class="hint">PNG, JPG, WEBP</small></span>
            <input type="file" name="picture" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" required title="Choose the source image that will carry the QR signal." />
          </label>

          <label>
            <span>Mode <small class="hint">Output style</small></span>
            <select name="mode" title="Choose how the QR should be generated.">
              <option value="subtle" {% if form.mode == "subtle" %}selected{% endif %}>Subtle Camera QR</option>
              <option value="color" {% if form.mode == "color" %}selected{% endif %}>Colored Photo QR</option>
              <option value="mosaic" {% if form.mode == "mosaic" %}selected{% endif %}>Picture Mosaic QR</option>
              <option value="data" {% if form.mode == "data" %}selected{% endif %}>Data QR</option>
              <option value="brand" {% if form.mode == "brand" %}selected{% endif %}>Brand QR</option>
            </select>
          </label>

          <label>
            <span>Text or URL <small class="hint">What the phone opens</small></span>
            <input type="text" name="text" value="{{ form.text }}" placeholder="https://example.com" title="Enter the URL or text encoded into subtle and brand QR modes." />
          </label>

          <div class="inline-fields">
            <label>
              <span>QR color <small class="hint">Color mode</small></span>
              <input type="color" name="qr_color" value="{{ form.qr_color }}" title="Sets the visible QR module color in Colored Photo QR mode." />
            </label>
            <label>
              <span>Opacity <small class="hint">Color mode</small></span>
              <input type="number" name="opacity" value="{{ form.opacity }}" min="0.15" max="1.00" step="0.01" title="Controls how strongly the colored QR is drawn over the original photo." />
            </label>
          </div>

          <div class="inline-fields">
            <label>
              <span>QR coverage <small class="hint">Subtle</small></span>
              <input type="number" name="scale" value="{{ form.scale }}" min="0.35" max="0.95" step="0.01" title="Controls how much of the image short side the subtle QR occupies." />
            </label>
            <label>
              <span>Scan strength <small class="hint">Subtle</small></span>
              <input type="number" name="strength" value="{{ form.strength }}" min="8" max="100" title="Controls how strongly the QR luminance is blended. Raise it if phones cannot scan." />
            </label>
          </div>

          <div class="inline-fields">
            <label>
              <span>Light blend <small class="hint">Subtle</small></span>
              <input type="number" name="light_blend" value="{{ form.light_blend }}" min="0.05" max="1.00" step="0.01" title="Controls how strongly light QR modules blend into highlight tones. Raise it if scans fail on textured photos." />
            </label>
            <label>
              <span>Min short side <small class="hint">Pixels</small></span>
              <input type="number" name="min_short_side" value="{{ form.min_short_side }}" min="256" max="2400" title="Upscales small images so camera scanners can resolve the QR modules." />
            </label>
          </div>

          <div class="inline-fields">
            <label>
              <span>Placement <small class="hint">Subtle</small></span>
              <select name="placement" title="Controls where the subtle QR is placed. Auto searches for a calmer image region.">
                <option value="auto" {% if form.placement == "auto" %}selected{% endif %}>Auto placement</option>
                <option value="center" {% if form.placement == "center" %}selected{% endif %}>Center</option>
                <option value="top-left" {% if form.placement == "top-left" %}selected{% endif %}>Top left</option>
                <option value="top-right" {% if form.placement == "top-right" %}selected{% endif %}>Top right</option>
                <option value="bottom-left" {% if form.placement == "bottom-left" %}selected{% endif %}>Bottom left</option>
                <option value="bottom-right" {% if form.placement == "bottom-right" %}selected{% endif %}>Bottom right</option>
              </select>
            </label>
          </div>

          <label>
            <span>Max short-side <small class="hint">Data mode</small></span>
            <input type="number" name="max_size" value="{{ form.max_size }}" min="4" max="64" title="Controls source-image sampling size for Data QR mode." />
          </label>

          <button class="generate" type="submit" title="Generate the selected QR image.">Generate Image</button>
        </div>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
      </form>

      <section class="panel stage">
        <div class="stage-header">
          <div>
            <h2>Scan signal, cinematic finish.</h2>
            <p>Use Colored Photo QR when the photo should stay intact with a visible colored scan signal over it.</p>
          </div>
          <div class="mode-badge">{{ form.mode|replace("-", " ") }}</div>
        </div>

        <div class="preview">
          <div class="preview-frame">
            {% if qr_path %}
            <img src="{{ qr_path }}" alt="Generated QR image preview" />
            {% else %}
            <div class="empty-state">
              <div class="scanner-icon" aria-hidden="true"></div>
              <p>Upload an image, enter a URL, and generate a camera-readable export. The final PNG appears here.</p>
            </div>
            {% endif %}
          </div>
        </div>

        <div class="actions">
          {% if qr_path %}
          <a class="action-link primary" href="{{ qr_path }}" download>Download PNG</a>
          <a class="action-link" href="{{ qr_path }}">Open Output</a>
          {% else %}
          <span class="hint">Output actions appear after generation.</span>
          {% endif %}
        </div>
      </section>
    </section>

    <section class="panel explain">
      <p class="panel-title">Controls</p>
      <div class="explain-grid">
        <article class="explain-item">
          <h3>Picture</h3>
          <p>The source artwork. Color mode keeps it intact, mosaic mode samples it into QR modules, and subtle mode blends a QR signal into its luminance.</p>
        </article>
        <article class="explain-item">
          <h3>Mode</h3>
          <p>Colored Photo QR draws a visible colored QR over the original photo, Picture Mosaic QR turns the photo into modules, Subtle Camera QR blends into the picture, Brand QR places a logo in a standard QR, and Data QR encodes sampled image data.</p>
        </article>
        <article class="explain-item">
          <h3>Text or URL</h3>
          <p>The destination encoded into Colored Photo QR, Picture Mosaic QR, Subtle Camera QR, and Brand QR. Short URLs scan more reliably.</p>
        </article>
        <article class="explain-item">
          <h3>QR Color</h3>
          <p>Sets the overlay color for Colored Photo QR. Bright cyan, pink, or green usually stand out well against photos.</p>
        </article>
        <article class="explain-item">
          <h3>Opacity</h3>
          <p>Sets how strongly the colored QR is drawn. Higher values are easier to see and usually easier to scan.</p>
        </article>
        <article class="explain-item">
          <h3>QR Coverage</h3>
          <p>Sets the subtle QR size relative to the image. Larger coverage improves scan reliability but is more noticeable.</p>
        </article>
        <article class="explain-item">
          <h3>Scan Strength</h3>
          <p>Sets luminance contrast. Lower values look cleaner; higher values are easier for phone cameras to detect.</p>
        </article>
        <article class="explain-item">
          <h3>Light Blend</h3>
          <p>Sets how much the light QR modules push into highlight tones. Textured photos usually need more than flat logos.</p>
        </article>
        <article class="explain-item">
          <h3>Min Short Side</h3>
          <p>Upscales small images before blending so QR modules have enough pixels for scanners to resolve.</p>
        </article>
        <article class="explain-item">
          <h3>Placement</h3>
          <p>Auto searches for a quieter region. Manual corners are useful when you want to protect faces, logos, or text.</p>
        </article>
        <article class="explain-item">
          <h3>Max Short-Side</h3>
          <p>Used only by Data QR mode to control how much of the source image is sampled into QR payload data.</p>
        </article>
        <article class="explain-item">
          <h3>Generate Image</h3>
          <p>Creates the PNG export. Test it with your phone, then adjust strength or coverage if scanning is inconsistent.</p>
        </article>
      </div>
    </section>
  </main>
</body>
</html>
"""

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index() -> str | bytes:
    error = None
    qr_path = None
    form = {
        "mode": "subtle",
        "text": "",
        "max_size": 16,
        "scale": "0.40",
        "strength": 65,
        "light_blend": "0.80",
        "min_short_side": 768,
        "placement": "auto",
        "qr_color": "#00e5ff",
        "opacity": "0.82",
    }

    if request.method == "POST":
        if "picture" not in request.files:
            error = "Missing picture file"
        else:
            file = request.files["picture"]
            mode = request.form.get("mode", "data")
            max_size = int(request.form.get("max_size", 16) or 16)
            scale = float(request.form.get("scale", 0.40) or 0.40)
            strength = int(request.form.get("strength", 65) or 65)
            light_blend = float(request.form.get("light_blend", 0.80) or 0.80)
            min_short_side = int(request.form.get("min_short_side", 768) or 768)
            placement = request.form.get("placement", "auto")
            qr_color = request.form.get("qr_color", "#00e5ff")
            opacity = float(request.form.get("opacity", 0.82) or 0.82)
            text = (request.form.get("text") or "").strip()
            form.update(
                {
                    "mode": mode,
                    "text": text,
                    "max_size": max_size,
                    "scale": f"{scale:.2f}",
                    "strength": strength,
                    "light_blend": f"{light_blend:.2f}",
                    "min_short_side": min_short_side,
                    "placement": placement,
                    "qr_color": qr_color,
                    "opacity": f"{opacity:.2f}",
                }
            )

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
                    elif mode == "mosaic":
                        if not text:
                            raise ValueError("Text or URL is required for picture mosaic QR mode")
                        qr_img = qr_from_image_mosaic(uploaded_img, data=text)
                    elif mode == "color":
                        if not text:
                            raise ValueError("Text or URL is required for colored photo QR mode")
                        qr_img = qr_from_colored_photo_overlay(
                            uploaded_img,
                            data=text,
                            color=qr_color,
                            scale=scale,
                            opacity=opacity,
                            min_short_side=min_short_side,
                            placement=placement,
                        )
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
                            light_strength_ratio=light_blend,
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
        HTML, error=error, qr_path=qr_path, form=form
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

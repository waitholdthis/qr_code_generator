# Cinematic QR Studio

Generate stylized, camera-scannable QR codes from text, URLs, logos, and photos. The project includes both a Click-powered CLI and a Flask upload UI.

## Features

- **Data mode**: converts a source image into a compact data QR payload.
- **Mosaic mode**: builds a QR code whose modules sample color from an image.
- **Color mode**: overlays a scannable QR structure onto a source photo.
- **Brand mode**: creates a high-resolution QR code with a centered logo.
- **Hidden mode**: blends a QR code into an image for subtle visual treatments.
- **Subtle mode**: generates camera-friendly subtle QR overlays with finder boost and placement controls.
- **Local or remote image input** for modes that accept image sources.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

## CLI usage

```bash
# Data QR from an image
python3 cli.py --mode data \
  --input tests/fixtures/logo.png \
  --output out/data.png \
  --max-size 16

# Photo-mosaic QR that encodes a URL
python3 cli.py --mode mosaic \
  --input tests/fixtures/logo.png \
  --text https://example.com \
  --output out/mosaic.png \
  --output-size 512

# Colored photo QR
python3 cli.py --mode color \
  --input tests/fixtures/logo.png \
  --text https://example.com \
  --qr-color '#00e5ff' \
  --opacity 0.82 \
  --output out/color.png

# Branded QR with a logo
python3 cli.py --mode brand \
  --input https://example.com \
  --logo tests/fixtures/logo.png \
  --output out/brand.png

# Subtle camera-scannable QR overlay
python3 cli.py --mode subtle \
  --input https://example.com \
  --logo tests/fixtures/logo.png \
  --placement auto \
  --output out/subtle.png
```

Run the full option list with:

```bash
python3 cli.py --help
```

## Flask upload UI

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:7860/
```

The UI accepts `png`, `jpg`, `jpeg`, and `webp` uploads up to 20 MB. Generated images are written to `uploads/` and served from `/files/<name>`.

> The built-in Flask server is for local/dev use. For production, run behind a production WSGI server such as Gunicorn.

## Development checks

```bash
python3 -m compileall -q .
python3 -m pytest -q
```

Current regression coverage includes:

- direct QR payload encoding, so text/URLs are not silently base64-mutated;
- local and remote image loading;
- CLI PNG generation;
- Flask upload/generation flow;
- malformed form input handling;
- generated-file path traversal protection.

## Notes

- Remote image loading is bounded to 20 MB and uses a request timeout.
- Numeric Flask form fields are clamped to safe ranges instead of raising server errors.
- Mosaic mode requires `--text`; it fails fast with a CLI usage error if omitted.

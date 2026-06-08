# QR Code Generator

Turn images into QR codes in two ways:
- **Data QR**: encode the image bytes into a QR payload and reconstruct an image with a minimised QR overlay.
- **Branded QR**: generate a normal QR code and embed/open a logo or image inside it.

## Quick start

```bash
python -m pip install -e .
```

## Commands

```bash
# data mode - encode image into QR, then reconstruct
qr -m data -i samples/photo.png -o out/data_qr.png

# brand mode - normal QR with image center logo
qr -m brand -i https://example.com -l samples/logo.png -o out/branded_qr.png
```

## Notes

- Data QR reconstruction is lossy and meant for small images.
- Brand mode keeps the QR scannable because the error correction absorbs the logo area.

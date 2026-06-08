from __future__ import annotations

import base64
import io
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
from PIL import Image

import core.qr_engine as qr_engine
import core.qr_hidden as qr_hidden
import helpers.image as image_helper
import helpers.logo as logo_helper


@click.command()
@click.option("-m", "--mode", required=True, type=click.Choice(["data", "brand", "hidden"], case_sensitive=False))
@click.option("-i", "--input", required=True, help="Image path/URL for `data` mode, text/URL for `brand` mode, or website/text for `hidden` mode.")
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path))
@click.option("-l", "--logo", required=False, type=click.Path(path_type=Path), help="Logo image for `brand`/`hidden` mode.")
@click.option("--max-size", default=48, show_default=True, help="Max short-side in cells for the data mode reconstruction.")
@click.option("--qr-size", default=256, show_default=True, help="QR code pixel size for hidden/brand mode.")
@click.option("--scale", default=0.22, show_default=True, help="Logo scale relative to canvas.")
@click.option("--alpha", default=175, show_default=True, help="QR alpha in hidden mode (0-255).")
def main(mode: str, input: str, output: Path, logo: Path | None, max_size: int, qr_size: int, scale: float, alpha: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    if mode.lower() == "data":
        img = image_helper.load_image(input)
        qr_img = qr_engine.qr_from_image(img, max_size=max_size, output_size=None)
        qr_img.save(str(output))
        click.echo(f"Saved data QR to {output}")
        return

    if mode.lower() == "brand":
        target = input
        if _looks_like_url(input):
            data = qr_engine.qr_from_data(target, output_size=2048)
        else:
            data = qr_engine.qr_from_data(target, output_size=2048)
        if logo is None:
            data.save(str(output))
            click.echo(f"Saved plain QR to {output}")
            return
        logo_img = image_helper.load_image(str(logo))
        branded = logo_helper.center_logo(qr_img=data, logo=logo_img)
        branded.save(str(output))
        click.echo(f"Saved branded QR to {output}")
        return
    if mode.lower() == "hidden":
        if logo is None:
            raise click.UsageError("--logo is required for hidden mode")
        logo_img = image_helper.load_image(str(logo))
        out = qr_hidden.qr_from_hidden(data=input, logo_path=str(logo), output_path=str(output), qr_size=qr_size, scale=scale, alpha=alpha)
        click.echo(f"Saved hidden QR image to {out}")
        return


def _looks_like_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Blur a PNG file in place by X percent.

How "percent" works:
    0%   -> no blur
    100% -> Gaussian blur radius = MAX_RADIUS_FRACTION * the image's shorter side
The blur scales with image size, so 20% looks about the same on a
small icon as it does on a large photo.

Usage:
    python blur_png.py image.png 25
    python blur_png.py image.png 50 --max-fraction 0.2
"""

import argparse
import os
import sys
import tempfile

from PIL import Image, ImageFilter

# At 100%, the blur radius is this fraction of the image's shorter side.
MAX_RADIUS_FRACTION = 0.10


def blur_png(path: str, percent: float, max_fraction: float = MAX_RADIUS_FRACTION) -> float:
    """Blur the PNG at `path` by `percent` (0-100) and overwrite it. Returns the radius used."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")

    with Image.open(path) as im:
        if im.format != "PNG":
            raise ValueError(f"{path} is not a PNG (detected: {im.format})")
        im.load()
        original_info = dict(im.info)

    radius = (percent / 100.0) * max_fraction * min(im.size)
    if radius <= 0:
        return 0.0  # Nothing to do

    # Normalize the color mode so the blur handles it correctly.
    if im.mode == "P":
        im = im.convert("RGBA" if "transparency" in im.info else "RGB")
    elif im.mode in ("1", "I", "I;16", "F", "CMYK"):
        im = im.convert("RGBA" if im.mode == "CMYK" else "L")

    # Blur with premultiplied alpha so transparent pixels don't leave dark halos.
    if im.mode == "RGBA":
        blurred = im.convert("RGBa").filter(ImageFilter.GaussianBlur(radius)).convert("RGBA")
    elif im.mode == "LA":
        blurred = im.convert("La").filter(ImageFilter.GaussianBlur(radius)).convert("LA")
    else:  # "L", "RGB"
        blurred = im.filter(ImageFilter.GaussianBlur(radius))

    # Write to a temp file first, then swap it in, so a crash can't corrupt the original.
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(suffix=".png", dir=directory)
    os.close(fd)
    try:
        save_kwargs = {}
        if "dpi" in original_info:
            save_kwargs["dpi"] = original_info["dpi"]
        blurred.save(tmp_path, format="PNG", optimize=True, **save_kwargs)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    return radius


def main() -> int:
    parser = argparse.ArgumentParser(description="Blur a PNG file in place by X percent.")
    parser.add_argument("file", help="Path to the PNG file (it will be overwritten)")
    parser.add_argument("percent", type=float, help="Blur amount, 0-100")
    parser.add_argument(
        "--max-fraction",
        type=float,
        default=MAX_RADIUS_FRACTION,
        help=f"Blur radius at 100%%, as a fraction of the shorter side (default {MAX_RADIUS_FRACTION})",
    )
    args = parser.parse_args()

    try:
        radius = blur_png(args.file, args.percent, args.max_fraction)
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Blurred {args.file} by {args.percent}% (radius {radius:.2f}px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

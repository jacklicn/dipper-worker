#!/usr/bin/env python3
"""Compute display size for an image while preserving aspect ratio.

Usage:
  python fit_image.py <image> --max-w <in> --max-h <in> [--unit in|cm|emu|px]
  python fit_image.py <image> --max-w 5.5 --max-h 3.2 --json

Prints width/height that fit inside the max box without stretching.
Requires Pillow (`pip install Pillow`) for reliable image probing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def probe_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError as e:
        raise SystemExit(
            "Error: Pillow is required. Install with: pip install Pillow"
        ) from e
    with Image.open(path) as im:
        w, h = im.size
    if w <= 0 or h <= 0:
        raise SystemExit(f"Error: invalid image size {w}x{h} for {path}")
    return w, h


def fit(src_w: int, src_h: int, max_w: float, max_h: float) -> tuple[float, float]:
    if max_w <= 0 or max_h <= 0:
        raise SystemExit("Error: --max-w and --max-h must be > 0")
    scale = min(max_w / src_w, max_h / src_h)
    return src_w * scale, src_h * scale


def convert(value_in_inches: float, unit: str) -> float:
    unit = unit.lower()
    if unit == "in":
        return value_in_inches
    if unit == "cm":
        return value_in_inches * 2.54
    if unit == "emu":
        return value_in_inches * 914400
    if unit == "px":
        # 96 CSS px per inch (presentation authoring convenience)
        return value_in_inches * 96
    raise SystemExit(f"Error: unknown unit {unit}")


def main() -> None:
    p = argparse.ArgumentParser(description="Fit image into a max box (aspect-safe).")
    p.add_argument("image", type=Path, help="Path to image file")
    p.add_argument("--max-w", type=float, required=True, help="Max width (inches)")
    p.add_argument("--max-h", type=float, required=True, help="Max height (inches)")
    p.add_argument(
        "--unit",
        default="in",
        choices=("in", "cm", "emu", "px"),
        help="Output unit for w/h (default: in)",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON")
    args = p.parse_args()

    if not args.image.is_file():
        raise SystemExit(f"Error: file not found: {args.image}")

    px_w, px_h = probe_size(args.image)
    # Treat pixel dimensions as a ratio only; box is in inches.
    fit_w_in, fit_h_in = fit(px_w, px_h, args.max_w, args.max_h)
    out_w = convert(fit_w_in, args.unit)
    out_h = convert(fit_h_in, args.unit)

    payload = {
        "path": str(args.image),
        "pixel_width": px_w,
        "pixel_height": px_h,
        "aspect": round(px_w / px_h, 6),
        "max_w_in": args.max_w,
        "max_h_in": args.max_h,
        "unit": args.unit,
        "width": round(out_w, 4) if args.unit != "emu" else int(round(out_w)),
        "height": round(out_h, 4) if args.unit != "emu" else int(round(out_h)),
        "width_in": round(fit_w_in, 4),
        "height_in": round(fit_h_in, 4),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"pixels={px_w}x{px_h} aspect={payload['aspect']} "
            f"fit={payload['width']}x{payload['height']} {args.unit} "
            f"(box {args.max_w}x{args.max_h} in)"
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""OCR images with RapidOCR (rapidocr_onnxruntime).

Prints structured JSON (schema dipper.ocr.v1, role=engine_draft) so the model
can apply linguistic correction on top of the raw engine output.

Usage:
    python ocr.py <image1> [image2 ...] [--detail json|text]

Examples:
    python ocr.py uploads/photo.png
    python ocr.py outputs/screenshot.png --detail text
    python ocr.py a.png b.png --detail json
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def _force_utf8_stdio() -> None:
    """Force UTF-8 stdout/stderr before any output.

    On Windows the console/pipe encoding defaults to GBK (cp936): JSON output
    containing CJK text or symbols outside GBK (emoji, ℃, circled digits, …)
    then raises UnicodeEncodeError and kills the script. This guarantees the
    emitted JSON is always valid UTF-8 regardless of locale/console codepage.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


_force_utf8_stdio()


def detect_engine():
    """Prefer rapidocr_onnxruntime; fall back to the unified `rapidocr` package."""
    try:
        from rapidocr_onnxruntime import RapidOCR

        return RapidOCR, "rapidocr_onnxruntime"
    except ImportError:
        try:
            from rapidocr import RapidOCR

            return RapidOCR, "rapidocr"
        except ImportError:
            return None, None


def _to_rgb(img: Image.Image) -> Image.Image:
    """Flatten transparent images onto white and return a plain RGB image.

    The engine's own 4-channel conversion swaps R/B channels; flattening
    beforehand keeps colors correct and avoids the engine's swap quirk.
    """
    if img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    ):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def _prepare(
    img: Image.Image,
    min_height: int,
    width_height_ratio: float,
    pre_scale: float = 1.0,
):
    """Return (engine-ready RGB array, inverse_map | None).

    rapidocr_onnxruntime silently *skips* text detection for short or very
    wide images: if h <= min_height or w/h > width_height_ratio, the whole
    image is fed to the recognizer as a single crop, which fails for wide thin
    strips (multi-line UI text, formula lines, code, tables) and yields empty
    results. Fix: upscale short images and pad wide strips vertically with white
    so the detector actually runs and finds each text line. `inverse_map` maps
    detected boxes back to original-image coordinates.
    """
    w, h = img.size
    scale = pre_scale
    if pre_scale != 1.0:
        img = img.resize(
            (round(w * pre_scale), round(h * pre_scale)), Image.LANCZOS
        )
        w, h = img.size

    pad_top = 0
    if h < min_height:
        up = max(2.0, math.ceil(min_height / max(h, 1)) + 1)
        scale *= up
        img = img.resize((round(w * up), round(h * up)), Image.LANCZOS)
        w, h = img.size

    if width_height_ratio > 0 and w > h * width_height_ratio:
        target_h = math.ceil(w / width_height_ratio)
        pad_top = (target_h - h) // 2
        padded = Image.new("RGB", (w, target_h), (255, 255, 255))
        padded.paste(img, (0, pad_top))
        img = padded

    arr = np.array(img)
    if scale == 1.0 and pad_top == 0:
        return arr, None

    def inverse_map(box):
        return [
            [round(pt[0] / scale, 1), round((pt[1] - pad_top) / scale, 1)]
            for pt in box
        ]

    return arr, inverse_map


def normalize_items(result):
    """Accept legacy list rows and the newer rapidocr result object."""
    if result is None:
        return []
    if hasattr(result, "txts"):
        txts = list(result.txts or [])
        boxes = list(result.boxes or [])
        scores = list(result.scores or [])
        out = []
        for i, text in enumerate(txts):
            out.append(
                {
                    "box": boxes[i] if i < len(boxes) else None,
                    "text": str(text),
                    "score": round(float(scores[i]), 4) if i < len(scores) else None,
                }
            )
        return out
    out = []
    for row in result:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        box, text = row[0], row[1]
        score = row[2] if len(row) > 2 else None
        out.append(
            {
                "box": box,
                "text": str(text),
                "score": round(float(score), 4) if score is not None else None,
            }
        )
    return out


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False))
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="OCR images with RapidOCR")
    ap.add_argument("paths", nargs="+", help="image file path(s)")
    ap.add_argument(
        "-detail",
        "--detail",
        dest="detail",
        choices=["json", "text"],
        default="json",
        help="json: full structured result (default); text: compact text-only payload",
    )
    args = ap.parse_args()

    paths = []
    for raw in args.paths:
        p = Path(raw)
        if not p.is_file():
            fail(f"file not found: {raw}")
        paths.append(p)

    engine_cls, engine_name = detect_engine()
    if engine_cls is None:
        fail(
            "rapidocr_onnxruntime not installed. Run: pip install rapidocr-onnxruntime"
        )

    try:
        engine = engine_cls()
    except Exception as exc:
        fail(f"failed to init OCR engine: {exc}")

    min_height = getattr(engine, "min_height", 30) or 30
    width_height_ratio = getattr(engine, "width_height_ratio", -1) or -1

    items = []
    no_text_files = []
    for p in paths:
        try:
            with Image.open(p) as raw:
                img = _to_rgb(raw)
        except Exception as exc:
            fail(f"cannot read image {p}: {exc}")

        try:
            arr, inverse_map = _prepare(img, min_height, width_height_ratio)
            result = engine(arr)
            if isinstance(result, tuple):
                result = result[0]
            file_items = normalize_items(result)

            # Detector found nothing: retry on a 2x upscale, which often
            # recovers blurry / low-resolution text.
            if not file_items:
                arr2, inverse2 = _prepare(
                    img, min_height, width_height_ratio, pre_scale=2.0
                )
                result = engine(arr2)
                if isinstance(result, tuple):
                    result = result[0]
                retry_items = normalize_items(result)
                if retry_items:
                    file_items = retry_items
                    inverse_map = inverse2

            for it in file_items:
                if it["box"] and inverse_map:
                    it["box"] = inverse_map(it["box"])
                it["file"] = str(p)
                items.append(it)

            if not file_items:
                no_text_files.append(str(p))
        except Exception as exc:
            fail(f"OCR failed for {p}: {exc}")

    text = "\n".join(it["text"] for it in items)

    notes = [
        "text/items are an engine draft - apply linguistic correction before quoting or acting.",
        "Fix look-alike / wrong-character errors (esp. Chinese glyphs); keep proper nouns and numbers unless clearly misread.",
        "Prioritize lines with score < 0.6 (low_confidence_lines); do not invent content unsupported by the draft.",
        "Use items[].box (4-point polygon) for spatial/UI structure when needed.",
    ]
    if no_text_files:
        notes.append(
            f"No text detected in {', '.join(no_text_files)}: the image may be "
            "blank, purely graphical, or contain text that is too small/blurry "
            "for this engine. If the image should contain text, ask the user "
            "for a zoomed-in or higher-resolution version."
        )

    if args.detail == "text":
        print(
            json.dumps(
                {
                    "schema": "dipper.ocr.v1",
                    "engine": engine_name,
                    "role": "engine_draft",
                    "text": text,
                    "guidance": {"notes": notes},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    scores = [it["score"] for it in items if it["score"] is not None]
    print(
        json.dumps(
            {
                "schema": "dipper.ocr.v1",
                "engine": engine_name,
                "role": "engine_draft",
                "text": text,
                "items": items,
                "stats": {
                    "lines": len(items),
                    "avg_score": round(sum(scores) / len(scores), 4) if scores else None,
                    "low_confidence_lines": sum(1 for s in scores if s < 0.6),
                },
                "guidance": {
                    "required_next_step": "model_linguistic_correction",
                    "notes": notes,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

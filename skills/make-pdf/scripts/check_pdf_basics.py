#!/usr/bin/env python3
"""Light structural checks for PDF files (pypdf).

Checks:
  - file opens as PDF
  - page_count >= 1
  - page boxes roughly consistent (same trim/media size)
  - optional text presence on first pages (warning if all empty)

Usage:
  python check_pdf_basics.py report.pdf
  python check_pdf_basics.py report.pdf --json

Exit 0 when status is ok (warnings allowed); exit 1 on errors.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def box_tuple(page) -> tuple[float, float, float, float] | None:
    box = page.mediabox
    if box is None:
        return None
    return (
        float(box.left),
        float(box.bottom),
        float(box.right),
        float(box.top),
    )


def size_of(box: tuple[float, float, float, float]) -> tuple[float, float]:
    return (round(box[2] - box[0], 2), round(box[3] - box[1], 2))


def check_file(path: Path) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {
            "status": "errors_found",
            "file": str(path),
            "error_count": 1,
            "errors": [{"message": "pypdf required: pip install pypdf"}],
            "warnings": [],
        }

    errors: list[dict] = []
    warnings: list[dict] = []

    try:
        reader = PdfReader(str(path))
    except Exception as e:
        return {
            "status": "errors_found",
            "file": str(path),
            "error_count": 1,
            "errors": [{"message": f"cannot open PDF: {e}"}],
            "warnings": [],
        }

    n = len(reader.pages)
    if n < 1:
        errors.append({"message": "PDF has zero pages"})

    sizes: list[tuple[float, float]] = []
    text_chars = 0
    for i, page in enumerate(reader.pages):
        b = box_tuple(page)
        if b is None:
            errors.append({"page": i + 1, "message": "missing mediabox"})
            continue
        sizes.append(size_of(b))
        if i < 5:
            try:
                t = page.extract_text() or ""
                text_chars += len(t.strip())
            except Exception:
                warnings.append({"page": i + 1, "message": "text extract failed"})

    if sizes:
        w0, h0 = sizes[0]
        for i, (w, h) in enumerate(sizes[1:], start=2):
            if abs(w - w0) > 1.0 or abs(h - h0) > 1.0:
                errors.append(
                    {
                        "page": i,
                        "message": "page size differs from page 1",
                        "page_size": [w, h],
                        "page1_size": [w0, h0],
                    }
                )

    if n >= 1 and text_chars == 0:
        warnings.append(
            {
                "message": "no extractable text on first pages (image-only or font encoding)",
            }
        )

    encrypted = bool(getattr(reader, "is_encrypted", False))
    meta = {}
    if reader.metadata:
        meta = {
            "title": reader.metadata.title,
            "author": reader.metadata.author,
        }

    status = "ok" if not errors else "errors_found"
    return {
        "status": status,
        "file": str(path),
        "page_count": n,
        "page1_size_pt": list(sizes[0]) if sizes else None,
        "encrypted": encrypted,
        "metadata": meta,
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Basic PDF open / page-size checks.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.pdf.is_file():
        print(json.dumps({"status": "errors_found", "error": f"not found: {args.pdf}"}))
        raise SystemExit(1)
    result = check_file(args.pdf)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()

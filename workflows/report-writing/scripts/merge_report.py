#!/usr/bin/env python3
"""Merge a report's chapters into one final markdown document.

Usage:
    python merge_report.py <report-dir> [--out <path>]

Reads <report-dir>/outline.md for the report title and chapter order, then
concatenates each chapter file from <report-dir>/chapters/ (in outline order)
into a single document with the report title as H1. Default output is
<report-dir>/report.md.

Exit codes:
    0  merged successfully
    1  a chapter listed in the outline has no file (nothing written)
    2  usage or structure errors
"""

import argparse
import re
import sys
from pathlib import Path

CHAPTER_RE = re.compile(r"^###\s+(\d+)\s+(.+?)\s*$")
TITLE_RE = re.compile(r"^# Report Outline:\s+(.+?)\s*$")


def chapter_order(outline: Path):
    """Return [(num, title)] in outline order."""
    order = []
    for line in outline.read_text(encoding="utf-8").splitlines():
        m = CHAPTER_RE.match(line)
        if m:
            order.append((m.group(1), m.group(2)))
    return order


def chapter_file(chapters_dir: Path, num: str):
    """First markdown file in chapters_dir named <num>-* (e.g. 03-overview.md)."""
    if not chapters_dir.is_dir():
        return None
    prefix = num + "-"
    for f in sorted(chapters_dir.iterdir()):
        if f.is_file() and f.suffix.lower() == ".md" and f.name.startswith(prefix):
            return f
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge report chapters into one markdown document.")
    parser.add_argument("report_dir", help="report root (contains outline.md and chapters/)")
    parser.add_argument("--out", default=None, help="output path (default <report-dir>/report.md)")
    args = parser.parse_args()

    root = Path(args.report_dir)
    outline = root / "outline.md"
    if not outline.is_file():
        print(f"outline.md not found in {root}", file=sys.stderr)
        return 2

    try:
        outline_text = outline.read_text(encoding="utf-8")
        order = chapter_order(outline)
    except OSError as exc:
        print(f"cannot read outline: {exc}", file=sys.stderr)
        return 2
    if not order:
        print("outline.md declares no chapters", file=sys.stderr)
        return 2

    chapters_dir = root / "chapters"
    missing = [num for num, _ in order if chapter_file(chapters_dir, num) is None]
    if missing:
        print(f"missing chapter files: {', '.join(missing)}", file=sys.stderr)
        return 1

    m = TITLE_RE.search(outline_text)
    parts = [f"# {m.group(1).strip() if m else 'Report'}\n"]
    for num, _ in order:
        f = chapter_file(chapters_dir, num)
        parts.append(f.read_text(encoding="utf-8").strip())
        parts.append("")

    out = Path(args.out) if args.out else root / "report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"merged {len(order)} chapters -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

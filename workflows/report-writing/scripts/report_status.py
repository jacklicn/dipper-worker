#!/usr/bin/env python3
"""Report progress/index view and validation for the report-writing workflow.

Usage:
    python report_status.py <report-dir>

Reads <report-dir>/outline.md, lists each chapter (number, title, status, file,
word count), and flags missing chapter files and placeholder markers. Gives a
compact index of the report without loading the chapter bodies, so the agent can
decide what to read back (chapter-block-level retrieval) and can resume a report
from the first non-drafted chapter.

Exit codes:
    0  every outline chapter has a file and no placeholders were found
    1  missing chapters or placeholder markers (reasons on stderr)
    2  usage or structure errors (no outline.md, unreadable directory)
"""

import re
import sys
from pathlib import Path

CHAPTER_RE = re.compile(r"^###\s+(\d+)\s+(.+?)\s*$")
STATUS_RE = re.compile(r"^\s*-\s*Status:\s*(\S+)")
PLACEHOLDER_RE = re.compile(
    r"TODO|TBD|lorem ipsum|待补充|占位|未完待续|\bXXX\b|\[\[.*?\]\]", re.IGNORECASE
)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")


def word_count(text: str) -> int:
    """CJK characters count as words; Latin runs split by whitespace/hyphens."""
    cjk = len(CJK_RE.findall(text))
    latin = len(WORD_RE.findall(text))
    return cjk + latin


def parse_outline(outline: Path):
    """Return (report_title, [ {num,title,status} ]) in outline order."""
    title = None
    chapters = []
    current = None
    for line in outline.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m and title is None:
            title = m.group(1).removeprefix("Report Outline:").strip()
        m = CHAPTER_RE.match(line)
        if m:
            if current:
                chapters.append(current)
            current = {"num": m.group(1), "title": m.group(2), "status": "planned"}
            continue
        if current is not None:
            m = STATUS_RE.match(line)
            if m:
                current["status"] = m.group(1)
    if current:
        chapters.append(current)
    return title, chapters


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
    if len(sys.argv) < 2:
        print("usage: report_status.py <report-dir>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    outline = root / "outline.md"
    if not outline.is_file():
        print(f"outline.md not found in {root}", file=sys.stderr)
        return 2

    try:
        title, chapters = parse_outline(outline)
    except OSError as exc:
        print(f"cannot read outline: {exc}", file=sys.stderr)
        return 2

    chapters_dir = root / "chapters"
    problems = []
    counts = {}
    print(f"Report: {title or '(untitled)'}")
    print(f"{'#':<4} {'status':<9} {'file':<36} {'words':>7}  title")
    for ch in chapters:
        status = ch["status"]
        counts[status] = counts.get(status, 0) + 1
        f = chapter_file(chapters_dir, ch["num"])
        if f is None:
            print(f"{ch['num']:<4} {status:<9} {'<missing>':<36} {'-':>7}  {ch['title']}")
            problems.append(f"chapter {ch['num']} has no file")
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        words = word_count(text)
        rel = str(f.relative_to(root))
        print(f"{ch['num']:<4} {status:<9} {rel:<36} {words:>7}  {ch['title']}")
        hits = PLACEHOLDER_RE.findall(text)
        if hits:
            problems.append(
                f"chapter {ch['num']} has placeholder markers: {sorted(set(h.upper() for h in hits))}"
            )
    if not chapters:
        problems.append("outline.md declares no chapters")

    print(f"\nStatus summary: {counts or 'none'}  (total chapters {len(chapters)})")
    if problems:
        print("Problems:", file=sys.stderr)
        for p in problems:
            print(f"- {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

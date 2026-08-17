#!/usr/bin/env python3
"""Validate SVG files (or HTML files containing inline SVG).

Usage:
    python validate_svg.py <file.svg|file.html> [file...]

Checks:
  - standalone .svg files must be well-formed XML
  - an <svg> root element exists
  - width/height (numeric) or viewBox is present
  - at least one visible child element exists

Exit code 0 = all valid, 1 = at least one problem (printed to stdout).
"""

import re
import sys
import xml.etree.ElementTree as ET

SVG_BLOCK_RE = re.compile(r"<svg\b[^>]*>[\s\S]*?</svg\s*>", re.IGNORECASE)
SVG_OPEN_RE = re.compile(r"<svg\b([^>]*)>", re.IGNORECASE)


def _attr_is_numeric(attrs, name):
    m = re.search(r"\b%s\s*=\s*[\"']([^\"']*)[\"']" % name, attrs, re.IGNORECASE)
    if not m:
        return False
    return bool(re.fullmatch(r"\d+(?:\.\d+)?(?:px|%)?", m.group(1).strip().lower()))


def _check_content(svg_xml, src):
    """Checks shared by the XML path and the lenient HTML path."""
    problems = []
    m = SVG_OPEN_RE.search(svg_xml)
    if not m:
        problems.append(f"{src}: no <svg> opening tag found")
        return problems
    attrs = m.group(1)
    if not (_attr_is_numeric(attrs, "width") and _attr_is_numeric(attrs, "height")) and not re.search(
        r"\bviewBox\s*=", attrs, re.IGNORECASE
    ):
        problems.append(f"{src}: <svg> needs numeric width and height, or a viewBox")
    inner = svg_xml[m.end():]
    inner = re.sub(r"<defs\b[\s\S]*?</defs\s*>", "", inner, flags=re.IGNORECASE)
    if not re.search(r"<\w", inner):
        problems.append(f"{src}: <svg> is empty (no child elements)")
    return problems


def check_file(path_str):
    try:
        with open(path_str, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return [f"{path_str}: cannot read: {exc}"]
    if not text.strip():
        return [f"{path_str}: file is empty"]

    if path_str.lower().endswith(".svg"):
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            return [f"{path_str}: XML parse error: {exc}"]
        tag = root.tag.lower()
        if tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
            return [f"{path_str}: root element is <{root.tag}>, expected <svg>"]
        return _check_content(text, path_str)

    blocks = SVG_BLOCK_RE.findall(text)
    if not blocks:
        return [f"{path_str}: no <svg>...</svg> block found"]
    problems = []
    for i, block in enumerate(blocks):
        problems += _check_content(block, f"{path_str}[svg {i + 1}]")
    return problems


def main(argv):
    files = argv[1:]
    if not files:
        print("Usage: python validate_svg.py <file.svg|file.html> [file...]")
        return 2
    problems = 0
    for name in files:
        found = check_file(name)
        if found:
            for line in found:
                print(line)
            problems += 1
        else:
            print(f"{name}: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

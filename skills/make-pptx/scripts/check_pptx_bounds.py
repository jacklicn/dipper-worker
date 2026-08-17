#!/usr/bin/env python3
"""Maintainer smoke helper: PPTX package + shape bounds (stdlib only).

Not part of the agent delivery path — agents must write valid decks via
pptxgenjs on first writeFile. This script only supports local smoke_create.

Usage:
  python check_pptx_bounds.py deck.pptx
  python check_pptx_bounds.py deck.pptx --json

Exit 0 when OK; exit 1 when issues are found.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

# Default 16:9 EMUs (13.333" x 7.5") — overridden from presentation.xml when present
DEFAULT_CX = 12192000
DEFAULT_CY = 6858000
TOLERANCE_EMU = 20000  # ~0.02" slack for rounding

REQUIRED_PARTS = (
    "[Content_Types].xml",
    "ppt/presentation.xml",
    "ppt/_rels/presentation.xml.rels",
)


def local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def normalize_zip_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def resolve_rel_target(base_dir: str, target: str) -> str:
    t = unquote(target.replace("\\", "/"))
    if t.startswith("/"):
        return t.lstrip("/")
    parts = [p for p in base_dir.split("/") if p] + [p for p in t.split("/") if p]
    out: list[str] = []
    for p in parts:
        if p == "..":
            if out:
                out.pop()
        elif p != ".":
            out.append(p)
    return "/".join(out)


def slide_size_emus(zf: zipfile.ZipFile) -> tuple[int, int]:
    try:
        root = ET.fromstring(zf.read("ppt/presentation.xml"))
    except KeyError:
        return DEFAULT_CX, DEFAULT_CY
    for el in root.iter():
        if local(el.tag) == "sldSz":
            cx = int(el.attrib.get("cx", DEFAULT_CX))
            cy = int(el.attrib.get("cy", DEFAULT_CY))
            return cx, cy
    return DEFAULT_CX, DEFAULT_CY


def list_slide_parts(zf: zipfile.ZipFile) -> list[str]:
    names = [
        n
        for n in zf.namelist()
        if re.match(r"ppt/slides/slide\d+\.xml$", normalize_zip_name(n))
    ]

    def key(n: str) -> int:
        m = re.search(r"slide(\d+)\.xml$", normalize_zip_name(n))
        return int(m.group(1)) if m else 0

    return sorted(names, key=key)


def shape_boxes(slide_xml: bytes) -> list[dict]:
    root = ET.fromstring(slide_xml)
    boxes: list[dict] = []
    for el in root.iter():
        if local(el.tag) != "xfrm":
            continue
        off = ext = None
        for child in list(el):
            name = local(child.tag)
            if name == "off":
                off = child
            elif name == "ext":
                ext = child
        if off is None or ext is None:
            continue
        try:
            x = int(off.attrib.get("x", "0"))
            y = int(off.attrib.get("y", "0"))
            cx = int(ext.attrib.get("cx", "0"))
            cy = int(ext.attrib.get("cy", "0"))
        except ValueError:
            continue
        boxes.append({"x": x, "y": y, "cx": cx, "cy": cy})
    return boxes


def collect_internal_rel_targets(zf: zipfile.ZipFile, names: set[str]) -> set[str]:
    targets: set[str] = set()
    for name in names:
        if not name.endswith(".rels") or "/_rels/" not in name:
            continue
        parent = name.rpartition("/_rels/")[0]
        try:
            root = ET.fromstring(zf.read(name))
        except (KeyError, ET.ParseError):
            continue
        for el in root:
            if local(el.tag) != "Relationship":
                continue
            target = el.attrib.get("Target")
            if not target:
                continue
            mode = (el.attrib.get("TargetMode") or "Internal").lower()
            if mode == "external":
                continue
            targets.add(resolve_rel_target(parent, target))
    return targets


def check_rels(zf: zipfile.ZipFile, rels_path: str, base_dir: str, names: set[str]) -> list[dict]:
    errors: list[dict] = []
    try:
        root = ET.fromstring(zf.read(rels_path))
    except KeyError:
        errors.append({"message": f"missing rels: {rels_path}"})
        return errors
    except ET.ParseError as e:
        errors.append({"message": f"rels parse error: {rels_path}: {e}"})
        return errors
    for el in root:
        if local(el.tag) != "Relationship":
            continue
        target = el.attrib.get("Target")
        if not target:
            errors.append({"message": "relationship missing Target", "rels": rels_path})
            continue
        mode = (el.attrib.get("TargetMode") or "Internal").lower()
        if mode == "external":
            continue
        resolved = resolve_rel_target(base_dir, target)
        if resolved not in names:
            errors.append(
                {
                    "message": "broken relationship target",
                    "rels": rels_path,
                    "id": el.attrib.get("Id"),
                    "target": target,
                    "resolved": resolved,
                }
            )
    return errors


def check_package(zf: zipfile.ZipFile, names: set[str]) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    for part in REQUIRED_PARTS:
        if part not in names:
            errors.append({"message": f"missing required part: {part}"})

    referenced = collect_internal_rel_targets(zf, names)

    if "[Content_Types].xml" in names:
        try:
            ct_root = ET.fromstring(zf.read("[Content_Types].xml"))
            has_pres = False
            for el in ct_root:
                if local(el.tag) != "Override":
                    continue
                part_name = normalize_zip_name(el.attrib.get("PartName", "")).lstrip("/")
                if part_name == "ppt/presentation.xml":
                    has_pres = True
                if part_name and part_name not in names:
                    entry = {
                        "message": "Content_Types Override points to missing part",
                        "part": part_name,
                    }
                    # pptxgenjs often lists unused slideMasterN Overrides; warn unless referenced.
                    if part_name in referenced:
                        errors.append(entry)
                    else:
                        warnings.append(entry)
            if not has_pres and "ppt/presentation.xml" in names:
                errors.append(
                    {"message": "Content_Types missing Override for ppt/presentation.xml"}
                )
        except ET.ParseError as e:
            errors.append({"message": f"[Content_Types].xml parse error: {e}"})

    if "ppt/_rels/presentation.xml.rels" in names:
        errors.extend(
            check_rels(zf, "ppt/_rels/presentation.xml.rels", "ppt", names)
        )

    for slide in list_slide_parts(zf):
        base = slide.rsplit("/", 1)[0]  # ppt/slides
        fname = slide.rsplit("/", 1)[-1]
        rels = f"{base}/_rels/{fname}.rels"
        if rels in names:
            errors.extend(check_rels(zf, rels, base, names))

    return errors, warnings


def check_file(path: Path) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    slides_checked = 0
    shapes_checked = 0

    try:
        zf = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as e:
        return {
            "status": "errors_found",
            "file": str(path),
            "slides_checked": 0,
            "shapes_checked": 0,
            "error_count": 1,
            "errors": [{"message": f"not a valid ZIP/OOXML package: {e}"}],
            "warnings": [],
        }

    with zf:
        names = {normalize_zip_name(n) for n in zf.namelist()}
        pkg_errors, pkg_warnings = check_package(zf, names)
        errors.extend(pkg_errors)
        warnings.extend(pkg_warnings)

        slide_w, slide_h = slide_size_emus(zf)
        parts = list_slide_parts(zf)
        if not parts:
            errors.append(
                {
                    "slide": None,
                    "message": "no ppt/slides/slideN.xml parts found",
                }
            )
        for part in parts:
            slides_checked += 1
            try:
                boxes = shape_boxes(zf.read(part))
            except ET.ParseError as e:
                errors.append({"slide": part, "message": f"slide XML parse error: {e}"})
                continue
            for i, b in enumerate(boxes):
                shapes_checked += 1
                right = b["x"] + b["cx"]
                bottom = b["y"] + b["cy"]
                problems = []
                if b["x"] < -TOLERANCE_EMU:
                    problems.append("left")
                if b["y"] < -TOLERANCE_EMU:
                    problems.append("top")
                if right > slide_w + TOLERANCE_EMU:
                    problems.append("right")
                if bottom > slide_h + TOLERANCE_EMU:
                    problems.append("bottom")
                if problems:
                    errors.append(
                        {
                            "slide": part,
                            "shape_index": i,
                            "box_emu": b,
                            "slide_size_emu": {"cx": slide_w, "cy": slide_h},
                            "overflow": problems,
                        }
                    )

    status = "ok" if not errors else "errors_found"
    return {
        "status": status,
        "file": str(path),
        "slides_checked": slides_checked,
        "shapes_checked": shapes_checked,
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Check PPTX package integrity and shape bounds vs slide size."
    )
    ap.add_argument("pptx", type=Path, help="Path to .pptx")
    ap.add_argument("--json", action="store_true", help="Always print JSON")
    args = ap.parse_args()

    if not args.pptx.is_file():
        print(json.dumps({"status": "errors_found", "error": f"not found: {args.pptx}"}))
        raise SystemExit(1)

    result = check_file(args.pptx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()

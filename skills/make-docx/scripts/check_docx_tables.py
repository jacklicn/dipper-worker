#!/usr/bin/env python3
"""Maintainer smoke helper: DOCX package + table width checks (stdlib only).

Not part of the agent delivery path — agents must write valid files via the
`docx` library on first save. This script only supports local smoke_create.

Usage:
  python check_docx_tables.py report.docx
  python check_docx_tables.py report.docx --json

Exit 0 when OK; exit 1 when issues are found.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from urllib.parse import unquote

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TOLERANCE_DXA = 20  # ~0.014 inch

REQUIRED_PARTS = (
    "[Content_Types].xml",
    "word/document.xml",
    "word/_rels/document.xml.rels",
)


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def q(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def attr(el: ET.Element, name: str, default: str | None = None) -> str | None:
    return el.attrib.get(q(name), el.attrib.get(name, default))


def normalize_zip_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def resolve_rel_target(base_dir: str, target: str) -> str:
    """Resolve a Relationship Target relative to the .rels file directory."""
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


def check_package(zf: zipfile.ZipFile) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    names = {normalize_zip_name(n) for n in zf.namelist()}

    for part in REQUIRED_PARTS:
        if part not in names:
            errors.append({"message": f"missing required part: {part}"})

    if "[Content_Types].xml" not in names:
        return errors, warnings

    try:
        ct_root = ET.fromstring(zf.read("[Content_Types].xml"))
    except ET.ParseError as e:
        errors.append({"message": f"[Content_Types].xml parse error: {e}"})
        return errors, warnings

    referenced = collect_internal_rel_targets(zf, names)
    has_document_override = False
    for el in ct_root:
        tag = local(el.tag)
        if tag != "Override":
            continue
        part_name = normalize_zip_name(el.attrib.get("PartName", "")).lstrip("/")
        content_type = el.attrib.get("ContentType", "")
        if part_name == "word/document.xml":
            has_document_override = True
        if part_name and part_name not in names:
            entry = {
                "message": "Content_Types Override points to missing part",
                "part": part_name,
                "content_type": content_type,
            }
            # Dangling unused Overrides are a known writer quirk; only fail if referenced.
            if part_name in referenced:
                errors.append(entry)
            else:
                warnings.append(entry)

    if not has_document_override and "word/document.xml" in names:
        errors.append(
            {
                "message": "Content_Types missing Override for word/document.xml",
            }
        )

    rels_path = "word/_rels/document.xml.rels"
    if rels_path in names:
        try:
            rels_root = ET.fromstring(zf.read(rels_path))
        except ET.ParseError as e:
            errors.append({"message": f"document.xml.rels parse error: {e}"})
            return errors, warnings
        base_dir = "word"
        for rel in rels_path_iter(rels_root):
            target = rel.get("Target")
            if not target:
                errors.append({"message": "relationship missing Target"})
                continue
            mode = (rel.get("TargetMode") or "Internal").lower()
            if mode == "external":
                continue
            resolved = resolve_rel_target(base_dir, target)
            if resolved not in names:
                errors.append(
                    {
                        "message": "broken relationship target",
                        "id": rel.get("Id"),
                        "target": target,
                        "resolved": resolved,
                    }
                )

    return errors, warnings


def collect_internal_rel_targets(zf: zipfile.ZipFile, names: set[str]) -> set[str]:
    """All package parts pointed to by any .rels Relationship (Internal)."""
    targets: set[str] = set()
    for name in names:
        if not name.endswith(".rels"):
            continue
        # …/ _rels / foo.xml.rels → parent dir of the source part
        norm = normalize_zip_name(name)
        if "/_rels/" not in norm:
            continue
        parent, _, _leaf = norm.rpartition("/_rels/")
        base_dir = parent
        try:
            root = ET.fromstring(zf.read(name))
        except (KeyError, ET.ParseError):
            continue
        for rel in rels_path_iter(root):
            target = rel.get("Target")
            if not target:
                continue
            mode = (rel.get("TargetMode") or "Internal").lower()
            if mode == "external":
                continue
            targets.add(resolve_rel_target(base_dir, target))
    return targets


def rels_path_iter(rels_root: ET.Element):
    for el in rels_root:
        if local(el.tag) == "Relationship":
            yield {
                "Id": el.attrib.get("Id"),
                "Target": el.attrib.get("Target"),
                "TargetMode": el.attrib.get("TargetMode"),
            }


def parse_tables(document_xml: bytes) -> list[dict]:
    root = ET.fromstring(document_xml)
    tables: list[dict] = []
    for tbl in root.iter(q("tbl")):
        tbl_w = None
        tbl_type = None
        tbl_pr = tbl.find(q("tblPr"))
        if tbl_pr is not None:
            w_el = tbl_pr.find(q("tblW"))
            if w_el is not None:
                tbl_w = int(attr(w_el, "w") or "0")
                tbl_type = attr(w_el, "type") or "dxa"

        grid_cols: list[int] = []
        grid = tbl.find(q("tblGrid"))
        if grid is not None:
            for col in grid.findall(q("gridCol")):
                grid_cols.append(int(attr(col, "w") or "0"))

        cell_widths: list[list[int | None]] = []
        for tr in tbl.findall(q("tr")):
            row_ws: list[int | None] = []
            for tc in tr.findall(q("tc")):
                tc_pr = tc.find(q("tcPr"))
                w_val: int | None = None
                if tc_pr is not None:
                    tc_w = tc_pr.find(q("tcW"))
                    if tc_w is not None and (attr(tc_w, "type") or "dxa") == "dxa":
                        w_val = int(attr(tc_w, "w") or "0")
                row_ws.append(w_val)
            cell_widths.append(row_ws)

        tables.append(
            {
                "tbl_w": tbl_w,
                "tbl_type": tbl_type,
                "grid_cols": grid_cols,
                "cell_widths": cell_widths,
            }
        )
    return tables


def check_tables(tables: list[dict]) -> list[dict]:
    errors: list[dict] = []
    for i, t in enumerate(tables):
        if t["tbl_type"] == "pct":
            errors.append(
                {
                    "table_index": i,
                    "message": "table width type is pct; use dxa for portable layout",
                }
            )
        grid = t["grid_cols"]
        if not grid:
            errors.append({"table_index": i, "message": "missing tblGrid/gridCol"})
            continue
        grid_sum = sum(grid)
        if t["tbl_w"] is not None and abs(grid_sum - t["tbl_w"]) > TOLERANCE_DXA:
            errors.append(
                {
                    "table_index": i,
                    "message": "sum(gridCol) != tblW",
                    "tbl_w": t["tbl_w"],
                    "grid_sum": grid_sum,
                    "grid_cols": grid,
                }
            )
        for r, row in enumerate(t["cell_widths"]):
            # Skip complex rows (merged cells) when counts differ.
            if len(row) != len(grid):
                continue
            for c, (cell_w, col_w) in enumerate(zip(row, grid)):
                if cell_w is None:
                    continue
                if abs(cell_w - col_w) > TOLERANCE_DXA:
                    errors.append(
                        {
                            "table_index": i,
                            "row": r,
                            "col": c,
                            "message": "cell tcW != gridCol",
                            "tcW": cell_w,
                            "gridCol": col_w,
                        }
                    )
    return errors


def check_file(path: Path) -> dict:
    try:
        zf = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as e:
        return {
            "status": "errors_found",
            "file": str(path),
            "error_count": 1,
            "errors": [{"message": f"not a valid ZIP/OOXML package: {e}"}],
        }

    with zf:
        names = {normalize_zip_name(n) for n in zf.namelist()}
        errors, warnings = check_package(zf)
        tables: list[dict] = []
        if "word/document.xml" in names:
            try:
                tables = parse_tables(zf.read("word/document.xml"))
                errors.extend(check_tables(tables))
            except ET.ParseError as e:
                errors.append({"message": f"word/document.xml parse error: {e}"})

    return {
        "status": "ok" if not errors else "errors_found",
        "file": str(path),
        "tables_checked": len(tables),
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Check DOCX package integrity and table DXA width consistency."
    )
    ap.add_argument("docx", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.docx.is_file():
        print(json.dumps({"status": "errors_found", "error": f"not found: {args.docx}"}))
        raise SystemExit(1)
    result = check_file(args.docx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()

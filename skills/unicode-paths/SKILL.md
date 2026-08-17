---
name: unicode-paths
description: >-
  Cross-platform rules for reading/writing files whose names contain Chinese or
  other non-ASCII characters on Windows, macOS, and Linux. Use when paths fail
  with Chinese filenames, 中文文件名, 文件读取失败, garbled paths, NFC/NFD
  mismatch, or shell open/read of CJK names fails.
metadata: {"dipper-bot":{"emoji":"📁"}}
---

# Unicode / CJK Filenames

Avoid file-not-found and mojibake when paths contain Chinese or other non-ASCII
characters. Prefer Dipper filesystem tools over shell path plumbing.

## Prefer Dipper tools

1. Discover the real name with `list_dir`, `glob`, or `find` (do not guess).
2. Pass that **exact** string to `read_file` / `write_file` / `edit_file` /
   `download_url` destinations, or as the image path argument of the `rapidocr`
   OCR script.
3. Avoid `exec` for open/read/copy when the path contains Chinese or other
   non-ASCII — Node `fs` handles Unicode paths more reliably than `cmd`/default
   console encodings.
4. Keep Unicode in tool JSON arguments as-is. Do not rewrite names to pinyin or
   ASCII unless the user asks.

## Windows

- Default console code page is often **GBK/CP936**. Raw `cmd` (`type`, `dir`,
  unquoted paths) frequently fails or garbles Chinese names.
- Prefer built-in tools. If shell is required: **PowerShell** or **Python
  `pathlib`**, with UTF-8 (`chcp 65001`, `PYTHONUTF8=1`,
  `open(..., encoding="utf-8")`, `Path(...).read_text(encoding="utf-8")`).
- Always quote paths. Node accepts `/` and `\`; in `cmd` prefer quoted paths.
- Do not rely on 8.3 short names for CJK files.

## macOS

- APFS filenames may be stored as **UTF-8 NFD** (decomposed). A visually
  identical NFC string from memory can fail `exists` / open.
- Always use the basename returned by `list_dir` / `glob`, never re-type Chinese
  from recollection when a read fails.
- Quote paths in shell; Terminal is usually UTF-8.

## Linux

- Require a UTF-8 locale (`LANG` / `LC_ALL` like `zh_CN.UTF-8` or `en_US.UTF-8`).
  `LANG=C` breaks many shell operations on Chinese names.
- Quote every path. In scripts use `pathlib` + explicit `encoding="utf-8"`.

## Content encoding vs filename encoding

- **Filename**: Unicode path to the file (this skill).
- **File bytes**: text body encoding (usually UTF-8; some CN sources are GBK —
  see `stock` skill). A correct Unicode path can still yield mojibake if the
  **content** decoder is wrong — that is separate from "file not found".

## Recovery checklist

If `read_file` / converters report not found or fail on a Chinese name:

1. `list_dir` or `glob` the parent directory.
2. Copy the exact basename from the tool output (including Chinese).
3. Retry `read_file` (or markitdown/summarize) with that path.
4. Only if tools still fail: Python `pathlib` with UTF-8 — not raw `cmd`.
5. Do not mass-rename to ASCII unless the user requests it.

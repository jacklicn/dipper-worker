---
name: rapidocr
description: >-
  Use this skill for OCR (optical character recognition) on images: screenshots,
  photos, scanned documents, and any picture containing Chinese or English text.
  Triggers include 识别图片文字, 图片文字提取, OCR image, extract text from image,
  read text from screenshot/photo. Runs a Python script (rapidocr_onnxruntime)
  that returns structured JSON (text, line boxes, scores) for model analysis.
license: MIT
---

# RapidOCR — 图片文字识别

## When to use

Whenever the user provides an image (screenshot, photo, scan) and asks you to
read, extract, or transcribe its text — Chinese, English, or mixed. Image files
usually live under `uploads/` (user uploads) or `outputs/` (screenshots you
generated). Do **not** call `read_file` on binary images; use this skill instead.

## Install

The script needs `rapidocr-onnxruntime` (Python module `rapidocr_onnxruntime`).
Install once per Python environment:

```bash
python -m pip install -U pip
python -m pip install rapidocr-onnxruntime
```

**Python 3.13+**: the legacy `rapidocr-onnxruntime` wheels are capped at Python
`<3.13`. On newer interpreters install the maintained unified package instead
(the script auto-detects either):

```bash
python -m pip install rapidocr onnxruntime
```

If pip is slow or unreachable, use a mirror, e.g.
`python -m pip install rapidocr-onnxruntime -i https://mirrors.aliyun.com/pypi/simple/`.
The package bundles its detection/recognition models (PP-OCR), so it works
offline after install and covers Simplified Chinese + English out of the box.

**Encoding**: the script forces UTF-8 on stdout/stderr, so Chinese text and
symbols (℃, emoji, circled digits) always come out as valid UTF-8 regardless of
the Windows console/pipe codepage (GBK/cp936). No `PYTHONIOENCODING` /
`PYTHONUTF8` setup is required.

## Run the script

```bash
# Full structured JSON (default): text + per-line items with box + score
python skills/rapidocr/scripts/ocr.py uploads/photo.png

# Multiple images
python skills/rapidocr/scripts/ocr.py uploads/a.png uploads/b.png

# Compact text-only payload (saves tokens)
python skills/rapidocr/scripts/ocr.py outputs/screenshot.png --detail text
```

Resolve the real path first when names contain Chinese or other non-ASCII
characters (use `list_dir` / `glob`, then pass that exact path — see skill
`unicode-paths`). Prefer passing paths through the exec tool with the image
path as an argument; on Windows avoid raw `cmd` for CJK paths.

## Output

The script prints JSON (schema `dipper.ocr.v1`):

- `text` — all recognized lines joined in reading order (draft transcript).
- `items[]` — per line: `text`, `box` (4-point polygon), `score` (0–1), `file`.
- `stats` — line count, average score, low-confidence line count.
- `guidance.notes` — correction hints for the model.

## Pipeline (required)

1. Run the script; treat its output as an **engine draft** (`role=engine_draft`).
2. Apply **model linguistic correction** next: fix look-alike / wrong-character
   errors (especially Chinese glyph confusions) using sentence context, and
   prioritize lines with `score < 0.6`.
3. Only then quote, answer, or run further tools from the corrected text.
   Briefly note material corrections when they change meaning.
4. Use `items[].box` when spatial / UI layout matters (reading order, regions).

## Troubleshooting

- `ModuleNotFoundError: rapidocr_onnxruntime` → run the install command above,
  then retry. Prefer the workspace venv if one exists.
- Slow first run → the engine initializes ONNX sessions once; later runs reuse
  them. Keep the engine process alive for repeated OCR of many images.
- Very large images → downscale first if the engine is slow (Pillow is a
  dependency of rapidocr-onnxruntime).
- Wide / thin image strips (single UI line, formula, code line) → the script
  auto-pads them vertically with white and reruns, because the underlying
  engine otherwise skips text detection for images wider than ~8:1 and returns
  empty results. Detected boxes are mapped back to the original image.
- Transparent (RGBA/alpha) images → flattened onto a white background before
  OCR, so transparent backgrounds don't hide glyphs.
- Small / blurry text → the script retries once at 2x upscale when the first
  pass finds nothing; if still empty the image likely has no readable text, so
  ask the user for a zoomed-in or higher-resolution version.
- Skewed / rotated photos → try rotating the image 90° and re-running when the
  draft is empty or garbled.

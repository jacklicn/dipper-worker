---
name: make-pptx
description: "Create or update PowerPoint (.pptx) decks with pptxgenjs under an MIT skill. Use for slide decks, pitch decks, and presentations when the deliverable is a .pptx file. Do not use for Word, Excel, or PDF."
license: MIT
metadata: {"dipper":{"emoji":"📑","requires":{"bins":["node"],"npm":["pptxgenjs"]},"tools":["write_file","append_file","exec"]}}
---

# make-pptx

Build real OOXML presentations with **pptxgenjs**. This skill is original Dipper content under the MIT license (see `LICENSE`).

## When to use

- User wants a new `.pptx`, or edits to an existing deck that you regenerate from a script
- Mentions: slides, deck, presentation, pitch, 幻灯片, PPT

## Workflow

Correctness is decided **when the file is written**, not by post-hoc repair or conversion. Use only **pptxgenjs** `writeFile` — never hand-edit OOXML ZIP parts or rename `.html`/`.json` to `.pptx`.

1. **Lock the design system** (canvas, margins, type scale, palette) before writing slides.
2. **Pick one layout per slide** from the allowed set below — do not free-place boxes. Keep every shape inside the slide (`x ≥ margin`, `x+w ≤ canvas−margin`, same for `y`/`h`) so the deck opens cleanly.
3. Write a Node script that uses `pptxgenjs`. Follow **Content rules** and API notes below. **Never put the entire script in one `write_file`** — content is capped (~6KB per call). Use:
   - `write_file(path="outputs/build-pptx.js", content="<short skeleton>")` then
   - `append_file(path="outputs/build-pptx.js", content="<next chunk>")` as needed
   - or several small `edit_file` patches. Both `path` and `content` are required every call.
   For each image, run `scripts/fit_image.py` and use the returned `width`/`height` (inches). Use `pres.ShapeType.*` only (do not mix with `pres.shapes.*`).
4. `exec` the script so it saves under `outputs/documents/pptx/` with a semantic filename. Confirm exit 0 and the `.pptx` exists.
5. Optional: `python -m markitdown <file.pptx>` only to confirm **content** order — not to repair the binary. Stop. No per-slide screenshots, no visual subagents, no LibreOffice conversion, no fix-and-render loops.

Install pptxgenjs if missing: `npm install -g pptxgenjs` (or local `npm install pptxgenjs` next to the script).

## Design system (hard tokens)

Use these numbers unless the user supplies a brand kit:

| Token | Value |
|-------|--------|
| Canvas | `LAYOUT_WIDE` (16:9) |
| Margin | ≥ 0.5 in from every edge |
| Block gap | 0.3 in **or** 0.5 in (pick one, keep constant) |
| Title | 36–44 pt bold |
| Section | 20–24 pt bold |
| Body | 14–16 pt |
| Caption | 10–12 pt, muted |
| Title↔body contrast | ≥ 20 pt size difference |

**Palette:** one dominant color (60–70% visual weight), 1–2 supporting tones, one accent. Do not default to generic blue. Do not give every color equal weight.

**Fonts:** pair a distinctive header with a clean body (e.g. Georgia + Calibri, or Trebuchet MS + Calibri). Avoid “everything Arial” unless the user asks.

## Allowed layouts (one per slide)

| Layout | Use for |
|--------|---------|
| Cover | Title + subtitle; optional accent shape |
| Section | Chapter divider; short label |
| Left text / right media | Narrative + image or chart |
| Two column | Compare / pros-cons |
| KPI row | 3–4 large numbers with labels |
| Process | 3–5 numbered steps |
| Closing | Summary + next step / contact |

Vary layouts across the deck. Do not repeat the same title+bullets frame on every slide.

## Content rules

Build so the package is valid **on first write**:

- **Writer only:** `new PptxGenJS()` → `pres.writeFile({ fileName })`. Do not assemble ZIP/XML by hand.
- One idea per slide; if text overflows, **cut copy or split slides** — do not shrink below readable body size; do not place boxes past the slide edge.
- Body text left-aligned; center only titles or cover lines.
- Every content slide needs at least one non-text visual (shape, icon, chart, or image).
- No placeholder strings (`lorem`, `xxxx`, `this is a slide`, `待补充`).
- No decorative underline bars under titles.
- Strong contrast: no light-on-light or dark-on-dark icons/text.
- **Images:** path must exist; `w`/`h` from `fit_image.py` (no stretch).
- **Shapes:** `pres.ShapeType.rect` / `roundRect` / … only — one API family per script.
- **Script completeness:** finish the build script before `exec` (no truncated `write_file`).

## Images (aspect ratio required)

Never invent arbitrary `w`/`h` that stretch the asset.

```bash
python skills/make-pptx/scripts/fit_image.py path/to/image.png --max-w 5.5 --max-h 3.5 --json
```

Use the returned `width` / `height` (inches) in `addImage({ path, x, y, w, h })`.  
Slot rule: image box ≤ available content region; prefer **contain** (letterbox with background) over stretch.

## pptxgenjs essentials

```javascript
const PptxGenJS = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE"; // 16:9
pres.author = "Dipper";
pres.title = "Deck title";

const slide = pres.addSlide();
slide.background = { color: "F7F7F5" };

slide.addText("Slide title", {
  x: 0.5, y: 0.4, w: 12.3, h: 0.7,
  fontSize: 36, bold: true, fontFace: "Calibri", color: "1A1A1A",
  margin: 0,
});

slide.addText("Supporting point one\nSupporting point two", {
  x: 0.5, y: 1.4, w: 6.0, h: 3.5,
  fontSize: 16, fontFace: "Calibri", color: "333333",
  valign: "top", margin: 0,
});

// Prefer ShapeType (matches current pptxgenjs); do not mix with pres.shapes.*
slide.addShape(pres.ShapeType.rect, {
  x: 7.0, y: 1.4, w: 5.5, h: 3.5,
  fill: { color: "E8F0EC" },
  line: { color: "2F5D50", width: 1.5 },
});

const out = path.join("outputs", "documents", "pptx", "q3-overview.pptx");
fs.mkdirSync(path.dirname(out), { recursive: true });
pres.writeFile({ fileName: out });
```

More API notes: [references/pptxgenjs-basics.md](references/pptxgenjs-basics.md).

**Text box tip:** default text margins misalign boxes with shapes. Set `margin: 0` when aligning to icons or rules.

**Charts:** use `slide.addChart(...)` with explicit colors from the palette; label axes and units.

## Output storage

- **Location:** `outputs/documents/pptx/` only for finished decks. Scratch scripts stay under `outputs/`.
- **Naming:** keep Chinese names; English parts kebab-case; avoid `deck.pptx` / `output.pptx`. Revisions use `-v2`.
- **Format:** real OOXML via pptxgenjs — never rename `.html` / `.json` to `.pptx`.
- **Conflicts:** if the target exists with different content, write a `-v2` variant; never write into `uploads/` or `downloads/`.

## Skill maintainers (smoke only)

Not part of the agent delivery path. Local regression:

```bash
node skills/make-pptx/scripts/smoke_create.mjs
python skills/make-pptx/scripts/smoke_fit_image.py
```

## Dependencies

- Node.js + `pptxgenjs`
- `pip install Pillow` — `fit_image.py` (when embedding images)
- Optional content peek: `pip install "markitdown[pptx]"`

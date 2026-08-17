---
name: make-docx
description: "Create Word (.docx) documents with the npm docx library under an MIT skill. Use for reports, memos, letters, and formatted Word deliverables. Do not use for PowerPoint, Excel, or PDF."
license: MIT
metadata: {"dipper":{"emoji":"📄","requires":{"bins":["node"],"npm":["docx"]},"tools":["write_file","append_file","exec"]}}
---

# make-docx

Build real OOXML Word files with the **`docx`** npm package (`docx-js` API). Original Dipper content under MIT (see `LICENSE`).

## When to use

- User wants a new `.docx` (report, memo, letter, proposal, 报告, Word)
- Regenerating a document from a script is acceptable

For light text extraction of an existing file, `pandoc file.docx -t markdown` is enough; deep XML surgery of third-party docs is out of scope for this skill—prefer recreate with `docx` when feasible.

## Workflow

Correctness is decided **when the file is written**, not by post-hoc repair tools. Use only the official `docx` writer (`Packer.toBuffer` / `Packer.toFile`) — never hand-edit OOXML ZIP parts or rename `.md`/`.html` to `.docx`.

1. Lock page size, margins, and paragraph styles before writing body content.
2. Author a Node script using `docx` (`Document`, `Packer`, `Paragraph`, `Table`, …). Follow **Generation standards** below so Office opens the file without repair prompts. **Never put the entire script in one `write_file`** — content is capped (~6KB per call). Use:
   - `write_file(path="outputs/build-docx.js", content="<short skeleton>")` then
   - `append_file(path="outputs/build-docx.js", content="<next chunk>")` as needed
   - or several small `edit_file` patches. Both `path` and `content` are required every call.
3. For each image, run `scripts/fit_image.py` and convert inches → DXA (`× 1440`) for display size. Every `ImageRun` **must** include `type` and complete `altText` (`title`, `description`, `name`) — missing fields produce invalid packages.
4. `exec` the script so it writes under `outputs/documents/docx/` with a semantic filename. Confirm the script exits 0 and the `.docx` path exists.
5. Optional: `pandoc <file.docx> -t plain` (or `markitdown`) only to confirm **content** completeness — not to “fix” the binary. Stop. No PDF rasterization, no visual QA loops, no LibreOffice conversion.

Install if needed: `npm install -g docx` (or local `npm install docx`).

## Design system (hard tokens)

| Token | Value |
|-------|--------|
| Page | A4 for Chinese/international; US Letter for US audiences — **set explicitly** |
| Margins | 1440 DXA (1 in) on all sides unless user specifies |
| Body | 22–24 half-points (11–12 pt); Chinese: 微软雅黑 / 宋体; Latin: Calibri or Arial |
| Heading levels | At most 3; use built-in `HeadingLevel.HEADING_1/2/3` only |
| Heading outline | `outlineLevel` 0/1/2 on heading styles when overriding |
| Content width (Letter, 1" margins) | 9360 DXA |
| Content width (A4, 1" margins) | 9026 DXA |

**DXA:** 1440 DXA = 1 inch.

## Generation standards

Build so the package is valid **on first write**:

- **Writer only:** `new Document({…})` → `Packer.toBuffer` / `toFile`. Do not assemble ZIP/XML by hand.
- **Paragraphs:** one idea per `Paragraph`; never embed `\n` for new paragraphs.
- **Page breaks:** `new Paragraph({ children: [new PageBreak()] })` or `pageBreakBefore: true`.
- **Lists:** numbering config with bullet/decimal levels — never type `•` by hand.
- **Tables:** `WidthType.DXA` only (not percentage). Set table `width`, `columnWidths` (sum = table width), and matching cell `width`. Header row bold + light fill. Cell padding via cell margins. Wrong widths do not usually corrupt the file, but they break layout — set them correctly in the script.
- **Images:** pass `type` and complete `altText` (`title`, `description`, `name`). Size from `fit_image.py`; max width ≤ 80–100% of content width. Point `data` at real bytes that exist on disk.
- **Headers/footers:** optional; page numbers via `PageNumber.CURRENT`.
- **TOC:** only if headings use `HeadingLevel`; keep `headingStyleRange` aligned with levels used.
- **No empty spacer paragraphs** to fake vertical rhythm — use spacing on styles.
- **Script completeness:** the build script must be syntactically complete before `exec` (no truncated `write_file`); incomplete scripts yield missing or corrupt outputs.

## Images

```bash
python skills/make-docx/scripts/fit_image.py assets/chart.png --max-w 5.5 --max-h 4 --json
```

Convert inches to DXA for `transformation` / layout math: `Math.round(width_in * 1440)`.  
`ImageRun` still wants pixel-oriented `transformation: { width, height }` in many setups — prefer the library’s documented unit; keep aspect from `fit_image` either way (do not stretch).

## Minimal create example

```javascript
const { Document, Packer, Paragraph, TextRun, HeadingLevel,
        Header, Footer, PageNumber, AlignmentType } = require("docx");
const fs = require("fs");
const path = require("path");

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 24 } } }, // 12pt
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Calibri" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 }, // A4
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({ children: [new TextRun({ text: "Report", italics: true, size: 18 })] })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [PageNumber.CURRENT] })],
        })],
      }),
    },
    children: [
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Quarterly summary")],
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun("Body text goes here with a clear single thesis.")],
      }),
    ],
  }],
});

const out = path.join("outputs", "documents", "docx", "q3-summary.docx");
fs.mkdirSync(path.dirname(out), { recursive: true });
Packer.toBuffer(doc).then((buf) => fs.writeFileSync(out, buf));
```

Tables, lists, images: see [references/docx-js-basics.md](references/docx-js-basics.md).

## Output storage

- **Location:** finished files → `outputs/documents/docx/`; scratch under `outputs/`.
- **Naming:** keep Chinese filenames; English kebab-case; avoid `doc.docx` / `output.docx`. Revisions → `-v2`.
- **Format:** real OOXML via `docx` — never rename `.md`/`.html` to `.docx`.
- **Conflicts:** write `-v2` instead of overwriting different content; never write into `uploads/` or `downloads/`.

## Skill maintainers (smoke only)

Not part of the agent delivery path. Local regression:

```bash
node skills/make-docx/scripts/smoke_create.mjs
python skills/make-docx/scripts/smoke_fit_image.py
```

## Dependencies

- Node.js + `docx` (npm)
- `pip install Pillow` — `fit_image.py` (when embedding images)
- Optional content peek: `pandoc` or `markitdown`

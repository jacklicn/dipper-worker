---
name: make-pdf
description: "Create or process PDF files with reportlab/pypdf under an MIT skill. Use when the deliverable or primary input is a .pdf (generate reports, merge/split, extract text). Do not use for Word, PowerPoint, or Excel as the primary deliverable."
license: MIT
metadata: {"dipper":{"emoji":"📕","requires":{"pip":["reportlab","pypdf"]},"tools":["write_file","exec"]}}
---

# make-pdf

Generate and process PDFs with **reportlab** (create) and **pypdf** / **pdfplumber** (read, merge, split). Original Dipper content under MIT (see `LICENSE`).

## When to use

- New PDF reports, handouts, printable one-pagers
- Merge / split / rotate / encrypt existing PDFs
- Mentions: PDF, 导出 PDF, printable document

Form filling and heavy OCR belong to specialized flows; for scanned text prefer the workspace OCR skill after rasterizing pages.

## Workflow (create)

1. Lock **one** page size for the whole file (A4 or Letter) and margins.
2. Prefer **Platypus** flowables (`SimpleDocTemplate`, `Paragraph`, `Table`, `Image`, `PageBreak`) over hand-placed `canvas.drawString` coordinates.
3. Register a **CJK-capable font** when the body includes Chinese/Japanese/Korean.
4. Size images with `scripts/fit_image.py`; keep aspect ratio; max width ≤ content width.
5. Author a **complete** Python script. Persist it with **both** required args — never omit `path`:
   `write_file(path="outputs/build-pdf.py", content="<entire script>")`
   Then `exec` it so the PDF lands under `outputs/documents/pdf/` with a semantic filename.
6. Verify once:
   ```bash
   python skills/make-pdf/scripts/check_pdf_basics.py outputs/documents/pdf/name.pdf
   ```
7. Stop. No page-screenshot visual QA loops.

## Design system (hard tokens)

| Token | Value |
|-------|--------|
| Page | A4 (`210×297 mm`) for Chinese/international; Letter for US — same size on every page |
| Margins | ≥ 0.6 in (≈ 43 pt); keep ≥ 36 pt clear at the bottom for footers |
| Body | 10–11 pt; Title 18–24 pt; Heading1 14–16 pt |
| Line spacing | leading ≈ fontSize × 1.3 |
| Content width | page width − left − right margins |
| Images | contain inside box; never stretch |

## Generation standards

- **One pagesize** for the entire document.
- **Sub/superscripts:** inside `Paragraph` use `<sub>` / `<super>` — never Unicode ₀₁₂ / ⁰¹² (built-in fonts often draw black boxes).
- **CJK:** register a local TTF/OTF (Noto Sans CJK / Source Han / 微软雅黑) via `pdfbase.ttfonts.TTFont`; do not rely on Helvetica for Chinese.
- **Bounds:** if you must use `canvas`, compute y from `height - margin - offset`; never guess off-page coordinates.
- **Tables:** header row styled; keep within content width.
- **No placeholders** (`lorem`, `xxxx`, `待补充`).

## Images

```bash
python skills/make-pdf/scripts/fit_image.py assets/fig.png --max-w 5.5 --max-h 4 --unit in --json
```

Pass the fitted inches × 72 as points to reportlab `Image(path, width=..., height=...)`.

## Minimal create example (Platypus)

```python
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Optional CJK — point at a real font file on the machine:
# pdfmetrics.registerFont(TTFont("BodyCJK", "C:/Windows/Fonts/msyh.ttc"))

out = Path("outputs/documents/pdf/q3-brief.pdf")
out.parent.mkdir(parents=True, exist_ok=True)

doc = SimpleDocTemplate(
    str(out),
    pagesize=A4,
    leftMargin=0.75 * inch,
    rightMargin=0.75 * inch,
    topMargin=0.75 * inch,
    bottomMargin=0.75 * inch,
)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Body", parent=styles["Normal"], fontSize=11, leading=14))
# styles["Body"].fontName = "BodyCJK"

story = [
    Paragraph("Q3 Brief", styles["Title"]),
    Spacer(1, 12),
    Paragraph("One clear thesis paragraph. H<sub>2</sub>O uses sub tags.", styles["Body"]),
    PageBreak(),
    Paragraph("Appendix", styles["Heading1"]),
    Paragraph("Secondary detail.", styles["Body"]),
]
doc.build(story)
```

Merge/split and canvas notes: [references/reportlab-basics.md](references/reportlab-basics.md).

## Common processing (pypdf)

```python
from pypdf import PdfReader, PdfWriter

writer = PdfWriter()
for name in ["a.pdf", "b.pdf"]:
    for page in PdfReader(name).pages:
        writer.add_page(page)
with open("outputs/documents/pdf/merged.pdf", "wb") as f:
    writer.write(f)
```

Text/tables from existing PDFs: `pdfplumber` is preferred for layout-aware extraction.

## Output storage

- **Location:** `outputs/documents/pdf/`; temps under `outputs/`.
- **Naming:** keep Chinese names; English kebab-case; avoid `output.pdf` / `document.pdf`. Revisions → `-v2`.
- **Format:** valid PDF; after merge/split, spot-check with `check_pdf_basics.py`.
- **Conflicts:** write `-v2`; never write into `uploads/` or `downloads/`.

## Verification (once)

```bash
python skills/make-pdf/scripts/check_pdf_basics.py outputs/documents/pdf/q3-brief.pdf
```

Fix page-size mismatches or empty files only; re-run once.

Skill maintainers / local smoke:

```bash
python skills/make-pdf/scripts/smoke_create.py
python skills/make-pdf/scripts/smoke_fit_image.py
```

## Dependencies

- `pip install reportlab pypdf` (create + checker)
- `pip install pdfplumber` (optional extraction)
- `pip install Pillow` — `fit_image.py`
- System CJK font file when generating Chinese text

---
name: make-xlsx
description: "Create Excel (.xlsx) workbooks with openpyxl/pandas under an MIT skill. Use for spreadsheets, models, tables, and CSV/TSV to xlsx conversion. Do not use for Word, PowerPoint, or PDF as the primary deliverable."
license: MIT
metadata: {"dipper":{"emoji":"📊","requires":{"pip":["openpyxl"]},"tools":["write_file","append_file","exec"]}}
---

# make-xlsx

Build real `.xlsx` files with **openpyxl** (formatting + formulas) and **pandas** (tabular I/O). Original Dipper content under MIT (see `LICENSE`).

## When to use

- New or updated spreadsheets (`.xlsx`, sometimes `.csv`/`.tsv` as export)
- Mentions: Excel, workbook, sheet, 表格, 模型, pivot-ready tables

## Workflow

Correctness is decided **when the file is written**. Use **openpyxl** / **pandas** to save a real `.xlsx` — never rename CSV/HTML to `.xlsx`, never hand-edit the ZIP, and do **not** run LibreOffice/`soffice` (or any headless converter) to “fix” or recalculate the workbook.

1. Choose tool: **pandas** for bulk tabular data; **openpyxl** when you need formulas, styles, multiple sheets, freeze panes.
2. Lock sheet structure (header row, units in headers, number formats) before filling numbers.
3. Author a Python script with **Excel formulas** for all calculations — do not compute in Python and hardcode results. Follow **Generation standards** below. **Never put the entire script in one `write_file`** — content is capped (~6KB per call). Use:
   - `write_file(path="outputs/build-xlsx.py", content="<short skeleton>")` then
   - `append_file(path="outputs/build-xlsx.py", content="<next chunk>")` as needed
   - or several small `edit_file` patches. Both `path` and `content` are required every call.
4. `exec` the script so it saves to `outputs/documents/xlsx/` with a semantic name. Confirm exit 0 and `wb.save(...)` completed (file exists, non-empty).
5. Stop. No screenshot QA, no LibreOffice conversion, no post-save “repair” loop. Excel computes formulas when the user opens the file.

## Design system (hard tokens)

| Token | Guidance |
|-------|----------|
| Font | One professional face (Arial / Calibri / 微软雅黑) for the whole book |
| Header | Bold + light fill; freeze first row (`freeze_panes = "A2"`) |
| Column widths | Dates ~12, amounts ~14, short text 12–18, long text 20–28 |
| Alignment | Numbers right, text left, headers center |
| Zebra | At most one light band color; never rainbow fills |
| Print | Set print area when the sheet is meant to print; fit-to-width preferred |

## Generation standards

Build so the workbook is valid **on first `wb.save`**:

- **Writer only:** `Workbook()` / `load_workbook` → `wb.save(path)`. Do not assemble ZIP/XML by hand.
- **At least one sheet** with real headers and data (or formulas); never deliver an empty book.
- **Formulas first** (see below); guard divisions (`IF` / `IFERROR`) so opening the file does not flood `#DIV/0!`.
- **Number formats** set on cells that need them; years as text when appropriate.
- **Do not** `load_workbook(..., data_only=True)` and then `save` — that destroys formulas.
- **Script completeness:** finish the build script before `exec` (no truncated `write_file`).

### Formulas first

```python
# Wrong — hardcoded Python total
ws["B10"] = sum(values)

# Right — spreadsheet stays live
ws["B10"] = "=SUM(B2:B9)"
```

- Put assumptions in dedicated input cells; reference them (`=$B$6`), do not bury magic numbers in formulas.
- Cross-sheet refs: `Sheet1!A1` (quote sheet names with spaces: `'Q3 Actual'!A1`).
- Guard divisions; avoid `#DIV/0!` (use `IF` / `IFERROR` when appropriate).
- Remember: DataFrame row `i` → Excel row `i + 1` when headers occupy row 1.

### Number formats

| Kind | Format / rule |
|------|----------------|
| Year | Text `"2024"`, not thousands-separated numbers |
| Currency | `$#,##0` or `¥#,##0`; state units in the header |
| Percent | `0.0%` default |
| Negatives | Prefer accounting-style parentheses when building financial sheets |
| Zeros | Optional `$#,##0;($#,##0);"-"` patterns |

### Financial color convention (only if no template)

| Meaning | Style |
|---------|--------|
| Inputs | Font blue `0000FF` |
| Formulas | Font black |
| Cross-sheet links | Font green `008000` |
| External links | Font red `FF0000` |
| Key assumptions | Fill yellow `FFFF00` |

When editing an existing workbook, **match its style** — never force this palette over an established template.

### Templates

Study the file first. Preserve sheet names, header language, and number formats. Additive changes beat wholesale restyling.

## Minimal create example

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from pathlib import Path

wb = Workbook()
ws = wb.active
ws.title = "Summary"

header_font = Font(name="Calibri", bold=True, color="1A1A1A")
header_fill = PatternFill("solid", fgColor="D9E2F3")
thin = Border(
    left=Side(style="thin", color="B0B0B0"),
    right=Side(style="thin", color="B0B0B0"),
    top=Side(style="thin", color="B0B0B0"),
    bottom=Side(style="thin", color="B0B0B0"),
)

headers = ["Item", "Amount ($)", "Share"]
for col, text in enumerate(headers, start=1):
    cell = ws.cell(1, col, text)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal="center")
    cell.border = thin

ws["A2"] = "Product A"
ws["B2"] = 1200
ws["A3"] = "Product B"
ws["B3"] = 800
ws["A4"] = "Total"
ws["B4"] = "=SUM(B2:B3)"
ws["C2"] = "=B2/$B$4"
ws["C3"] = "=B3/$B$4"

ws["B2"].number_format = "$#,##0"
ws["B3"].number_format = "$#,##0"
ws["B4"].number_format = "$#,##0"
ws["C2"].number_format = "0.0%"
ws["C3"].number_format = "0.0%"

ws.column_dimensions["A"].width = 18
ws.column_dimensions["B"].width = 14
ws.column_dimensions["C"].width = 10
ws.freeze_panes = "A2"

out = Path("outputs/documents/xlsx/product-mix.xlsx")
out.parent.mkdir(parents=True, exist_ok=True)
wb.save(out)
```

Pandas bulk path and more openpyxl notes: [references/openpyxl-basics.md](references/openpyxl-basics.md).

## Output storage

- **Location:** `outputs/documents/xlsx/` for finished workbooks; temp CSV/scripts under `outputs/`.
- **Naming:** keep Chinese names; English kebab-case; avoid `book1.xlsx` / `output.xlsx`. Revisions → `-v2`.
- **Format:** real xlsx via openpyxl/pandas; CSV/TSV exports UTF-8.
- **Conflicts:** write `-v2` instead of clobbering different content; never write into `uploads/` or `downloads/`.

## Skill maintainers (smoke only)

Not part of the agent delivery path. Local regression:

```bash
python skills/make-xlsx/scripts/smoke_create.py
```

## Dependencies

- `pip install openpyxl` (required)
- `pip install pandas` (optional; tabular analysis / CSV bridge)

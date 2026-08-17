# openpyxl / pandas basics — make-xlsx

Public libraries: [openpyxl](https://openpyxl.readthedocs.io/), [pandas](https://pandas.pydata.org/). Prefer upstream docs for full APIs.

## Install

```bash
pip install openpyxl pandas
```

## Create / save (openpyxl)

```python
from openpyxl import Workbook
wb = Workbook()
ws = wb.active
ws["A1"] = "Hello"
ws["B1"] = "=A1"
wb.save("outputs/documents/xlsx/demo.xlsx")
```

Save only via `wb.save` / pandas `to_excel`. Do not rename CSV to `.xlsx`, hand-edit the ZIP, or run LibreOffice/`soffice` to “fix” or precompute values — Excel calculates formulas when the user opens the file.

## Load / edit

```python
from openpyxl import load_workbook
wb = load_workbook("existing.xlsx")  # keeps formulas
ws = wb["Sheet1"]
ws["C3"] = "=A3+B3"
wb.save("outputs/documents/xlsx/existing-v2.xlsx")
```

**Warning:** `load_workbook(..., data_only=True)` reads cached values. Saving that workbook **destroys formulas**. Use a separate load for inspection only.

## Styles

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

ws["A1"].font = Font(name="Calibri", bold=True, size=12)
ws["A1"].fill = PatternFill("solid", fgColor="D9E2F3")
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.column_dimensions["A"].width = 18
ws.row_dimensions[1].height = 20
ws.freeze_panes = "A2"
```

## Number formats

```python
ws["B2"].number_format = "$#,##0"
ws["C2"].number_format = "0.0%"
ws["D2"].number_format = "0.0x"
```

## Multiple sheets

```python
ws2 = wb.create_sheet("Assumptions")
ws2["A1"] = "Growth"
ws2["B1"] = 0.05
# reference from Summary: =Assumptions!B1
```

## Pandas bridge

```python
import pandas as pd

df = pd.read_excel("inputs.xlsx", sheet_name=0)
# analyze / clean...
df.to_excel("outputs/documents/xlsx/clean.xlsx", index=False)

# For formulas + formatting after pandas export, open with openpyxl and layer formulas.
```

Tips:

- Force dtypes on read: `dtype={"id": str}`
- Parse dates: `parse_dates=["date"]`
- Large files: `usecols=[...]` or openpyxl `read_only=True` / `write_only=True`

## Formula checklist

- Test 2–3 sample references before filling a whole column
- Excel is 1-indexed; header row shifts DataFrame indices by +1
- Check denominators before `/`
- Prefer absolute refs (`$B$6`) for assumptions

# reportlab / pypdf basics — make-pdf

Public libraries: [reportlab](https://www.reportlab.com/docs/reportlab-userguide.pdf), [pypdf](https://pypdf.readthedocs.io/). Prefer upstream docs for full APIs.

## Install

```bash
pip install reportlab pypdf pdfplumber Pillow
```

## Page sizes

```python
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm
```

Stick to one `pagesize` for every page in the file.

## Platypus (preferred for multi-page text)

```python
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
```

Build a `story` list, then `doc.build(story)`.

## Sub / super

```python
Paragraph("E = mc<super>2</super> and H<sub>2</sub>O", styles["Normal"])
```

Do not paste Unicode subscript/superscript code points into standard fonts.

## CJK font registration

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("BodyCJK", "/path/to/NotoSansSC-Regular.otf"))
style = ParagraphStyle("Body", fontName="BodyCJK", fontSize=11, leading=14)
```

On Windows, `C:/Windows/Fonts/msyh.ttc` (Microsoft YaHei) often works; confirm the face index if using `.ttc`.

## Images

```python
from reportlab.platypus import Image
img = Image("fig.png", width=5.5 * inch, height=3.1 * inch)  # from fit_image.py
```

## Canvas (absolute drawing)

```python
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

c = canvas.Canvas("out.pdf", pagesize=A4)
width, height = A4
c.drawString(72, height - 72, "Top-left-ish at 1 inch margins")
c.save()
```

Reserve bottom margin; derive y from `height`, do not hardcode beyond the page.

## pypdf merge / split

```python
from pypdf import PdfReader, PdfWriter

# merge
w = PdfWriter()
for path in ["a.pdf", "b.pdf"]:
    for page in PdfReader(path).pages:
        w.add_page(page)
with open("merged.pdf", "wb") as f:
    w.write(f)

# split first page
r = PdfReader("in.pdf")
w = PdfWriter()
w.add_page(r.pages[0])
with open("page1.pdf", "wb") as f:
    w.write(f)
```

## pdfplumber extract

```python
import pdfplumber
with pdfplumber.open("in.pdf") as pdf:
    for page in pdf.pages:
        print(page.extract_text())
        print(page.extract_tables())
```

# pptxgenjs basics (make-pptx)

Short reference for the public [pptxgenjs](https://github.com/gitbrent/PptxGenJS) API. Prefer the npm package docs for full options.

## Setup

```bash
npm install pptxgenjs
# or: npm install -g pptxgenjs
```

```javascript
const PptxGenJS = require("pptxgenjs");
const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE"; // 16:9 — also LAYOUT_16x9, LAYOUT_16x10, LAYOUT_4x3
```

## Units

Coordinates and sizes are in **inches** by default on standard layouts.

Typical 16:9 content width ≈ `13.33 - 2 * margin`. With 0.5 in margins, usable width ≈ 12.33 in.

## Text

```javascript
slide.addText("Hello", {
  x: 0.5, y: 0.5, w: 12, h: 0.6,
  fontSize: 36, bold: true, fontFace: "Calibri",
  color: "1A1A1A", align: "left", valign: "middle",
  margin: 0,
});
```

Multi-run / bullets: pass an array of text objects, or use `\n` with `breakLine` options per pptxgenjs docs.

## Shapes

Use `pres.ShapeType.*` (current pptxgenjs). Do not mix with the older `pres.shapes.*` enum in the same script.

```javascript
slide.addShape(pres.ShapeType.rect, {
  x: 0, y: 0, w: 0.25, h: 7.5,
  fill: { color: "1E2761" }, line: { color: "1E2761" },
});
// also: ShapeType.roundRect, ShapeType.ellipse, …
```

## Images

```javascript
slide.addImage({ path: "photo.png", x: 7, y: 1.2, w: 5.5, h: 3.1 });
// or: data: "image/png;base64,...."
```

Always compute `w`/`h` with `scripts/fit_image.py` so the bitmap is not stretched.

## Charts

```javascript
slide.addChart(pres.charts.BAR, {
  x: 0.5, y: 1.2, w: 12, h: 5,
  series: [{ name: "Revenue", values: [12, 18, 22] }],
  categories: ["Q1", "Q2", "Q3"],
  showTitle: true, title: "Revenue ($m)",
});
```

Match series colors to the deck palette.

## Write

```javascript
await pres.writeFile({ fileName: "outputs/documents/pptx/name.pptx" });
```

Ensure the parent directory exists (`fs.mkdirSync(..., { recursive: true })`).  
Write only via pptxgenjs — do not hand-edit the ZIP or rename other formats to `.pptx`.

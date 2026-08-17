# docx (npm) basics — make-docx

Notes for the public [`docx`](https://www.npmjs.com/package/docx) package. Prefer upstream docs for exhaustive options.

## Install

```bash
npm install docx
# or: npm install -g docx
```

## Imports you usually need

```javascript
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, Header, Footer, PageNumber, PageBreak,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  LevelFormat, VerticalAlign,
} = require("docx");
```

## Page size (DXA)

| Paper | width | height |
|-------|------:|-------:|
| US Letter | 12240 | 15840 |
| A4 | 11906 | 16838 |

Margins example: `{ top: 1440, right: 1440, bottom: 1440, left: 1440 }` (1 inch).

Landscape: pass portrait width/height and set `orientation` to landscape per library docs (library swaps edges in OOXML).

## Paragraphs and breaks

```javascript
new Paragraph({ children: [new TextRun("One paragraph")] })
new Paragraph({ children: [new PageBreak()] })
new Paragraph({ pageBreakBefore: true, children: [new TextRun("New page")] })
```

Do not put newline characters inside a single run to fake paragraphs.

## Lists

Configure `numbering` on `Document` with `LevelFormat.BULLET` or `LevelFormat.DECIMAL`, then reference it from paragraphs. Do not insert Unicode bullet glyphs as plain text.

## Tables

```javascript
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

new Table({
  width: { size: 9026, type: WidthType.DXA },
  columnWidths: [4513, 4513],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders,
          width: { size: 4513, type: WidthType.DXA },
          shading: { fill: "E8EEF4", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun({ text: "Header", bold: true })] })],
        }),
        // second cell...
      ],
    }),
  ],
});
```

Rules:

- Always `WidthType.DXA`
- `sum(columnWidths) === table.width.size`
- Each cell `width` matches its column
- Prefer `ShadingType.CLEAR` for fills

## Images

```javascript
new Paragraph({
  children: [
    new ImageRun({
      type: "png",
      data: fs.readFileSync("chart.png"),
      transformation: { width: 480, height: 270 }, // keep aspect from fit_image
      altText: { title: "Chart", description: "Q3 revenue", name: "chart" },
    }),
  ],
})
```

`type` and all three `altText` fields are required by the library.

## Write file

Always write through the library so the package is complete on first save:

```javascript
const buf = await Packer.toBuffer(doc);
fs.mkdirSync("outputs/documents/docx", { recursive: true });
fs.writeFileSync("outputs/documents/docx/name.docx", buf);
```

Do not hand-edit OOXML ZIP entries or rename other formats to `.docx`.

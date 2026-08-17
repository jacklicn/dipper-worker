#!/usr/bin/env node
/**
 * Smoke: create a sample .docx (with a DXA table) and run check_docx_tables.py.
 * Usage (from repo / workspace root):
 *   node skills/make-docx/scripts/smoke_create.mjs
 */
import { createRequire } from "node:module";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const skillRoot = resolve(__dirname, "..");
const workspaceHint = resolve(skillRoot, "../..");
const smokeNm = join(workspaceHint, "outputs", "_office-smoke", "node_modules", "docx", "package.json");
const require = createRequire(existsSync(smokeNm) ? smokeNm : import.meta.url);
const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  Header,
  Footer,
  PageNumber,
  AlignmentType,
} = require("docx");

const outDir = join(workspaceHint, "outputs", "documents", "docx");
const outFile = join(outDir, "smoke-q3-summary.docx");

const TABLE_W = 9026; // A4 content width @ 1" margins
const COLS = [3010, 3010, 3006];

function cell(text, width, opts = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: "B0B0B0" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "B0B0B0" },
      left: { style: BorderStyle.SINGLE, size: 4, color: "B0B0B0" },
      right: { style: BorderStyle.SINGLE, size: 4, color: "B0B0B0" },
    },
    shading: opts.fill ? { fill: opts.fill } : undefined,
    children: [
      new Paragraph({
        children: [new TextRun({ text, bold: !!opts.bold, size: 20 })],
      }),
    ],
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 24 } } },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 32, bold: true, font: "Calibri" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 },
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              children: [new TextRun({ text: "Smoke report", italics: true, size: 18 })],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ children: [PageNumber.CURRENT] })],
            }),
          ],
        }),
      },
      children: [
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          children: [new TextRun("Quarterly summary (smoke)")],
        }),
        new Paragraph({
          spacing: { after: 200 },
          children: [
            new TextRun(
              "Body text for make-docx smoke: one thesis per paragraph, A4 + DXA table.",
            ),
          ],
        }),
        new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: COLS,
          rows: [
            new TableRow({
              children: [
                cell("Item", COLS[0], { bold: true, fill: "D9E2F3" }),
                cell("Q2", COLS[1], { bold: true, fill: "D9E2F3" }),
                cell("Q3", COLS[2], { bold: true, fill: "D9E2F3" }),
              ],
            }),
            new TableRow({
              children: [
                cell("Revenue", COLS[0]),
                cell("120", COLS[1]),
                cell("145", COLS[2]),
              ],
            }),
            new TableRow({
              children: [
                cell("Margin %", COLS[0]),
                cell("18", COLS[1]),
                cell("21", COLS[2]),
              ],
            }),
          ],
        }),
      ],
    },
  ],
});

mkdirSync(outDir, { recursive: true });
const buf = await Packer.toBuffer(doc);
writeFileSync(outFile, buf);
console.log(`wrote ${outFile}`);

const checker = join(__dirname, "check_docx_tables.py");
const check = spawnSync("python", [checker, outFile], { encoding: "utf8" });
process.stdout.write(check.stdout || "");
process.stderr.write(check.stderr || "");
process.exit(check.status === 0 ? 0 : 1);

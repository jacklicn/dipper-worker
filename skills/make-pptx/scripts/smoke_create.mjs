#!/usr/bin/env node
/**
 * Smoke: create a sample .pptx (in-bounds shapes) and run check_pptx_bounds.py.
 * Usage (from repo / workspace root):
 *   node skills/make-pptx/scripts/smoke_create.mjs
 */
import { createRequire } from "node:module";
import { existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const skillRoot = resolve(__dirname, "..");
const workspaceHint = resolve(skillRoot, "../..");
const smokeNm = join(
  workspaceHint,
  "outputs",
  "_office-smoke",
  "node_modules",
  "pptxgenjs",
  "package.json",
);
const require = createRequire(existsSync(smokeNm) ? smokeNm : import.meta.url);
const PptxGenJS = require("pptxgenjs");

const outDir = join(workspaceHint, "outputs", "documents", "pptx");
const outFile = join(outDir, "smoke-q3-overview.pptx");

const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE";
pres.author = "Dipper";
pres.title = "Smoke deck";

const cover = pres.addSlide();
cover.background = { color: "F7F7F5" };
cover.addShape(pres.ShapeType.rect, {
  x: 0.5,
  y: 0.5,
  w: 0.18,
  h: 2.2,
  fill: { color: "2F5D50" },
  line: { color: "2F5D50" },
});
cover.addText("Q3 Overview (smoke)", {
  x: 0.9,
  y: 2.4,
  w: 11.5,
  h: 0.8,
  fontSize: 40,
  bold: true,
  fontFace: "Georgia",
  color: "1A1A1A",
  margin: 0,
});
cover.addText("make-pptx smoke fixture — in-bounds layout", {
  x: 0.9,
  y: 3.3,
  w: 11.5,
  h: 0.5,
  fontSize: 16,
  fontFace: "Calibri",
  color: "555555",
  margin: 0,
});

const body = pres.addSlide();
body.background = { color: "F7F7F5" };
body.addText("Highlights", {
  x: 0.5,
  y: 0.4,
  w: 12.3,
  h: 0.7,
  fontSize: 36,
  bold: true,
  fontFace: "Calibri",
  color: "1A1A1A",
  margin: 0,
});
body.addText("Revenue up 12%\nMargin improved to 21%\nPipeline coverage 3.1x", {
  x: 0.5,
  y: 1.4,
  w: 6.0,
  h: 3.5,
  fontSize: 16,
  fontFace: "Calibri",
  color: "333333",
  valign: "top",
  margin: 0,
});
body.addShape(pres.ShapeType.roundRect, {
  x: 7.0,
  y: 1.4,
  w: 5.5,
  h: 3.5,
  fill: { color: "E8F0EC" },
  line: { color: "2F5D50", width: 1.5 },
});
body.addText("KPI", {
  x: 7.3,
  y: 2.5,
  w: 5.0,
  h: 0.6,
  fontSize: 28,
  bold: true,
  fontFace: "Calibri",
  color: "2F5D50",
  align: "center",
  margin: 0,
});

mkdirSync(outDir, { recursive: true });
await pres.writeFile({ fileName: outFile });
console.log(`wrote ${outFile}`);

const checker = join(__dirname, "check_pptx_bounds.py");
const check = spawnSync("python", [checker, outFile], { encoding: "utf8" });
process.stdout.write(check.stdout || "");
process.stderr.write(check.stderr || "");
process.exit(check.status === 0 ? 0 : 1);

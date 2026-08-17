---
name: draw
description: Generate charts and visualizations (including animated charts) via standalone HTML + Canvas/SVG/Chart.js in the workspace. Use for bar/line/pie charts and local browser preview—not draw.io flowcharts (use drawio skill + mcp_drawio_* for flowcharts, sequence diagrams, and draw.io links).
metadata: {"dipper-bot":{"emoji":"📊","requires":{},"tools":["write_file"]}}
---

# Draw (HTML Charts & Diagrams)

Create charts and diagrams by writing standalone HTML files with embedded Canvas or SVG and JavaScript. Use `write_file` to generate `.html` files in the workspace; the user opens them in a browser to view.

## When to use

Trigger on: chart, graph, visualization, **animation** (chart animation, moving bars, transitions), bar chart, line chart, pie chart, or any visual representation of **numeric data** in HTML.

**Not this skill:** editable draw.io / diagrams.net diagrams, cloud architecture canvases, or Mermaid→draw.io — use the **`drawio`** skill (`mcp_drawio_open_drawio_*`) when those MCP tools are listed.

Trigger on: diagram or flow chart only when the user wants a **local HTML file** or Chart.js/SVG output, not a draw.io editor link.

## Visual tone (avoid generic "AI" chart aesthetics)

Charts and diagrams should look **intentional**, not like a default template or stock dashboard.

- **Pick a concrete look** tied to the user’s context: report/print (muted, ink-on-paper), terminal/dev (dark + monospace), slides (high contrast, few colors), internal doc (flat, minimal chrome). Do **not** fall back to "generic SaaS dashboard" for every request.
- **Palette**: use **2–4 colors + neutrals**; one clear accent is enough. Avoid rainbow category colors, neon gradients, and purple–blue glow unless the user asks. Prefer off-whites, charcoal, or a single restrained accent (e.g. deep green, rust, slate).
- **Typography**: set fonts explicitly in Chart.js (`options.plugins.legend.labels.font`, scales, `defaults.font.family`) or in CSS for SVG/HTML. Prefer `system-ui` / a sensible system stack, or one face the user names. Avoid looking like "default Chart.js + Inter everywhere."
- **Decoration**: skip drop shadows, glassmorphism, heavy rounding, and decorative gradients unless requested. Clarity beats polish.
- **Labels and data**: real axis titles, units, and sources; no vague `Series 1` / `Dataset` / `Label` unless placeholders are unavoidable—then replace with meaningful names before delivery.
- **Diagrams (SVG)**: simple strokes, consistent corner radius, aligned grid. Prefer readable structure over glossy shapes.

If the user gives no style cue, choose **one** restrained direction (e.g. "print-safe grayscale + one accent") and state it briefly in the HTML `<title>` or a small caption—not a paragraph of marketing fluff.

## Workflow

1. Decide what to draw (chart type, data, labels).
2. Build the full HTML content (including `<html>`, `<head>`, `<body>`, Canvas/SVG, and `<script>`).
3. Use `write_file(path="outputs/chart.html", content="...")` to save it.
4. If the output contains SVG, validate it in one deterministic step instead of re-reading the file repeatedly:
   `python skills/draw/scripts/validate_svg.py outputs/chart.html`
   (if the workspace copy is missing, locate the bundled script with `glob("**/validate_svg.py")` and run that path). Fix only what the script reports, then re-run it once.
5. If the HTML references external JS/CSS from a CDN, run `localize_html(path="outputs/chart.html")` to download them into an `assets/` directory next to the file and rewrite the page to use relative paths — the page then works offline and the assets can be reused by other pages. In the Chinese UI this downloads from domestic mirrors (npmmirror/BootCDN) automatically, not official CDNs. Pure SVG with no external assets: skip `localize_html` entirely.
6. Tell the user: "Saved to `outputs/chart.html`. Open it in your browser to view."

## Option A: Chart.js (recommended for bar/line/pie)

Use Chart.js via CDN for quick charts; **override colors and fonts** so the result does not read as the default CDN demo (see **Visual tone** above). After writing the file, run `localize_html` on it so `chart.js` is downloaded beside the HTML and referenced locally instead of from the CDN.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Chart</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body>
  <canvas id="myChart" width="500" height="300"></canvas>
  <script>
    const ctx = document.getElementById('myChart').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['A', 'B', 'C', 'D'],
        datasets: [{
          label: 'Quarterly total',  // use a real legend label, not "Value" / "Series 1"
          data: [12, 19, 8, 15],
          // Example: restrained palette—swap for the user’s brand or context
          backgroundColor: 'rgba(45, 55, 72, 0.35)',
          borderColor: 'rgb(30, 41, 59)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true } },
        animation: { duration: 1200, easing: 'easeOutQuart' }
      }
    });
  </script>
</body>
</html>
```

Chart types: `'bar'`, `'line'`, `'pie'`, `'doughnut'`, `'radar'`. Adapt `labels` and `data` to the user’s data.

**Built-in animation:** Chart.js animates on first draw by default. Use `options.animation` to set `duration` (ms), `easing` (e.g. `'linear'`, `'easeOutQuart'`), or `animation: false` to disable.

**Live updates (animated data change):** keep a `Chart` instance and call `chart.data.datasets[0].data = newValues; chart.update();` — Chart.js will tween between old and new values.

## Option B: Vanilla Canvas

Use raw Canvas when you need custom shapes or no external deps:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Canvas Chart</title>
</head>
<body>
  <canvas id="c" width="500" height="300"></canvas>
  <script>
    const c = document.getElementById('c');
    const ctx = c.getContext('2d');
    const data = [60, 80, 45, 90, 70];
    const max = Math.max(...data);
    const barW = 60, gap = 40, padding = 40;
    const chartH = c.height - 2 * padding;

    ctx.fillStyle = '#334155';  // avoid default bright blue unless the user wants it
    data.forEach((v, i) => {
      const x = padding + i * (barW + gap);
      const h = (v / max) * chartH;
      const y = c.height - padding - h;
      ctx.fillRect(x, y, barW, h);
    });
  </script>
</body>
</html>
```

## Option C: SVG

Use SVG for diagrams, flow charts, or vector graphics:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SVG Diagram</title>
</head>
<body>
  <svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
    <rect x="20" y="20" width="80" height="40" fill="#475569" rx="4"/>
    <rect x="140" y="20" width="80" height="40" fill="#78716c" rx="4"/>
    <rect x="260" y="20" width="80" height="40" fill="#b45309" rx="4"/>
    <path d="M100 40 L140 40" stroke="#333" stroke-width="2" fill="none"/>
    <path d="M220 40 L260 40" stroke="#333" stroke-width="2" fill="none"/>
  </svg>
</body>
</html>
```

When the user only asked for "an SVG image", write it as a standalone `.svg` file
(`outputs/diagram.svg`) instead of wrapping it in an HTML page — one file, no extra steps.

After writing, run the bundled validator instead of eyeballing the output repeatedly:

```bash
python skills/draw/scripts/validate_svg.py outputs/diagram.svg
```

Only fix what the script reports, then re-run it once; stop once it prints `OK`.

## Option D: Animation (Canvas / Chart.js / SVG)

When the user asks for **animated** charts or motion:

### D1 — Chart.js (easiest)

- First render: `animation: { duration: 1500, easing: 'easeOutBounce' }` on `options`.
- Loop / ticker: `setInterval` or `requestAnimationFrame` + `chart.data.datasets[0].data = [...]; chart.update('active');` (use `'none'` as second arg to `update` for instant jump, or omit for smooth tween).

### D2 — Vanilla Canvas + `requestAnimationFrame`

Animate bars/lines by interpolating values each frame (e.g. `progress` from 0→1 with `easeOutCubic`), clear canvas, redraw:

```javascript
function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }
let t0 = performance.now();
const duration = 1500;
function frame(now) {
  const p = Math.min(1, (now - t0) / duration);
  const k = easeOutCubic(p);
  ctx.clearRect(0, 0, c.width, c.height);
  // draw bars with heights = data[i] * k
  if (p < 1) requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
```

### D3 — SVG + CSS or SMIL

- **CSS:** `@keyframes` on `transform` / `opacity`; apply `animation: name 2s ease forwards` to elements.
- **SVG `<animate>`:** e.g. `<circle><animate attributeName="r" from="0" to="50" dur="1s" fill="freeze"/></circle>` for simple attribute tweens.

Prefer **Chart.js animation** for standard charts; use **Canvas rAF** for custom physics or games; use **SVG/CSS** for diagrams and icons.

## Data embedding

Put data in the HTML as JSON or inline JS:

```javascript
const data = [[1, 2], [2, 4], [3, 3], [4, 6]];
// or
const labels = ["Q1", "Q2", "Q3", "Q4"];
const values = [100, 150, 120, 180];
```

## Checklist

- [ ] Full HTML document with `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`
- [ ] Correct charset `<meta charset="utf-8">`
- [ ] All strings escaped in embedded JS (quotes in JSON)
- [ ] Path under workspace (e.g. `outputs/`, `workspace/`)
- [ ] If animation requested: use `options.animation` (Chart.js), `requestAnimationFrame` (Canvas), or CSS/SVG animate
- [ ] SVG output validated with `validate_svg.py` until it prints `OK`
- [ ] **Visual tone**: deliberate palette and typography; no default "AI dashboard" look; meaningful legend and axis labels
- [ ] External CDN JS/CSS localized with `localize_html` (offline-capable, reusable assets)
- [ ] Inform user how to open the file

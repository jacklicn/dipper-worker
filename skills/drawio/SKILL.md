---
name: drawio
description: "Create editable flowcharts, architecture diagrams, org charts, and sequence diagrams in draw.io via @drawio/mcp. Use for draw.io, diagrams.net, Mermaid/CSV/XML diagrams, flowcharts, sequence diagrams, and architecture—not bar/line charts (use draw skill for HTML/Chart.js)."
metadata: {"dipper-bot":{"emoji":"📐","requires":{"bins":["npx"]},"tools":["mcp_drawio_open_drawio_xml","mcp_drawio_open_drawio_mermaid"]}}
---

# draw.io Diagrams (MCP Tool Server)

Open diagrams in the [draw.io](https://www.draw.io) editor via [`@drawio/mcp`](https://www.npmjs.com/package/@drawio/mcp). The server builds a `#create` URL; the user opens it in a browser to view and edit.

**Prerequisites:** `tools.mcpServers.drawio` in config (default in `DefaultConfig()`). Node.js + `npx` on PATH. Log `MCP connect failed` → check Node and `mcpCommandEnv` / PATH.

**Default tools:** `mcp_drawio_open_drawio_mermaid`, `mcp_drawio_open_drawio_xml` only. Add `"open_drawio_csv"` to `enabledTools` for CSV org charts.

## draw vs drawio

| User need | Use |
|-----------|-----|
| Bar/line/pie chart, animation, local HTML file | **`draw`** → `write_file` + Chart.js / Canvas |
| Flowchart, sequence, architecture, org chart in draw.io | **`drawio`** → `mcp_drawio_*` |

Never reply with ASCII art or prose-only “diagrams” when `mcp_drawio_*` is available.

## MCP tools

| Tool | When |
|------|------|
| `mcp_drawio_open_drawio_mermaid` | Default for flow, sequence, state, ER, Gantt, most graphs |
| `mcp_drawio_open_drawio_xml` | Cloud icons, swimlanes, layers, precise layout, `.drawio` export |
| `mcp_drawio_open_drawio_csv` | Only if enabled in config — org charts from tables |

**Parameters:** `content` (string, required), optional `lightbox` (bool), optional `dark` (`auto` | `true` | `false`).

## `content` rules (avoid syntax errors)

1. **Plain string only** — pass raw Mermaid/XML/CSV text. Do **not** wrap in JSON objects or markdown fences.
2. **No markdown code fences inside `content`** — do not put ` ```mermaid ` or ` ```xml ` inside the parameter; those fences break import.
3. **Mermaid**
   - Use `graph TD` / `flowchart LR` / `sequenceDiagram` etc. with valid syntax.
   - Node IDs: alphanumeric, no spaces (use `nodeA` not `node A`).
   - Labels with special characters: use quotes `A["Login (OAuth2)"]`.
   - Avoid experimental or version-specific features; keep diagrams ≤ ~25 nodes for first pass.
4. **XML** — include `mxfile` → `diagram` → `mxGraphModel` → `root` with `mxCell id="0"` and `id="1" parent="0"`. Follow the XML reference embedded in the tool description.
5. **Size** — prefer one page; split huge architectures into multiple diagrams if needed.

## Workflow

1. Pick format (Mermaid first unless XML/icons required).
2. Draft `content` using the rules above.
3. Call `mcp_drawio_open_drawio_*` in the **same turn**.
4. Return the **draw.io URL** as a markdown link.
5. **Always** add the paste-error reminder (see below) after the first successful link.

### Paste-error reminder (show to user)

Include something like:

> If the editor shows a syntax or parse error, **paste the full error message** here and I will fix the diagram and send a new link.

## Error recovery (user paste → fix → redraw)

The editor does **not** send parse errors back through MCP.

| Step | Action |
|------|--------|
| 1 | You deliver URL + paste-error reminder |
| 2 | User opens link; if broken, pastes **full** error text (or asks to fix/redraw) |
| 3 | You fix `content`, call `mcp_drawio_*` again **same turn**, deliver **new** URL |

**Rules**

- User pasted editor error or asked to redraw → **must** call `mcp_drawio_*` again; do not only paste corrected Mermaid in chat.
- Simplify on repeat errors (fewer nodes, simpler syntax).
- **MCP tool `Error:`** (args, npx, connection) → explain once; **do not** auto-retry in a loop. Wait for user-pasted editor error or a new request.

## Format examples

**Mermaid** (`content` body only):

```text
sequenceDiagram
    participant User
    participant API
    User->>API: POST /login
    API-->>User: 200 OK
```

**XML** — see tool description for full reference; minimal skeleton in repo docs.

## Example requests

| Request | Tool |
|---------|------|
| OAuth2 sequence | `mcp_drawio_open_drawio_mermaid` |
| Checkout flowchart | `mcp_drawio_open_drawio_mermaid` |
| AWS VPC architecture | `mcp_drawio_open_drawio_xml` |
| Org chart (CSV enabled) | `mcp_drawio_open_drawio_csv` or Mermaid |

## Troubleshooting

| Symptom | Action |
|---------|--------|
| No `mcp_drawio_*` tools | `npx -y @drawio/mcp`; fix `MCP connect failed` / PATH |
| MCP `Error:` | Explain; no auto-retry loop |
| Editor syntax error | User pastes error → fix `content` → redraw |
| Repeated failure | Smaller Mermaid; fewer nodes |
| User wanted HTML chart | **`draw`** skill |

## References

- [drawio-mcp](https://github.com/jgraph/drawio-mcp) · [AI FAQ](https://www.drawio.com/doc/faq/ai-drawio-generation) · [xml-reference.md](https://github.com/jgraph/drawio-mcp/blob/main/shared/xml-reference.md)

# Dipper Worker Built-in Skills

## Loading

1. Bundled under `skills/` (dev) and `dist/agent/builtin-skills/` (build).
2. Packaged apps also ship `resources/skills` via electron-builder `extraResources`.
3. `seedBuiltinSkills` copies missing skill directories into `{workspace}/skills/`.
4. System prompt lists skill names + `SKILL.md` paths; the agent uses `read_file` to load details.

Workspace skills override builtins when the same directory name already exists.

## Available Skills

| Skill | Notes |
|-------|--------|
| `ai-content-detector` | Forensic linguistics / AI-vs-human writing audit |
| `browser-operator` | Browser automation guidance |
| `clawhub` | Skill registry install |
| `cron` | Scheduling |
| `docx` / `pptx` / `xlsx` / `pdf` | Office / PDF pipelines + scripts |
| `emotional-support` | Emotional listening & psychological support |
| `draw` / `drawio` | Charts / diagrams |
| `fullstack-engineer` / `product-manager` / `qa-engineer` | Role skills |
| `github` | `gh` CLI |
| `markitdown` | Document conversion |
| `mcp-builder` | MCP server authoring |
| `memory` | Memory workflow |
| `rapidocr` | Image OCR via rapidocr_onnxruntime (Chinese/English, line boxes + scores) |
| `skill-creator` | Create/improve skills |
| `stock` | Tencent/Sina CN quotes & finance headlines (GBK + Referer) |
| `summarize` | URL / file / video summaries |
| `tmux` | tmux control |
| `unicode-paths` | Chinese / non-ASCII filenames on Windows, macOS, Linux |
| `weather` | Weather APIs |

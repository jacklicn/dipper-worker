---
name: markitdown
description: "Use when converting PDF, Word (.docx), Excel (.xlsx/.xls), or PowerPoint (.pptx) to Markdown for LLM analysis. Triggers include: markitdown, convert office or PDF to Markdown, stable text extraction before summarization. Prefer this pipeline before analyzing binary office/PDF content."
license: Proprietary. LICENSE.txt has complete terms
---

# MarkItDown: PDF / Office → Markdown (for LLM analysis)

## When to use

For **PDF, Word, Excel, or PowerPoint**, convert to **Markdown first**, then `read_file` or pass text to the model. This yields more stable structure (headings, lists, tables) than ad-hoc binary reads and matches how LLMs are typically trained (Markdown-friendly).

## Virtualenv at workspace root

Use the Agent **workspace** directory (`agents.workspace`, e.g. `~/.dipper-bot/workspace`):

```bash
cd /path/to/workspace
python3 -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows (cmd):
# .venv\Scripts\activate.bat
```

**dipper-bot `exec`**: when `working_dir` is the workspace, `python` / `python3` are rewritten to use `workspace/.venv` (the venv is created on first use if missing). You still need to **install MarkItDown once** inside that venv.

**Requirements**: Python **3.10+** (MarkItDown).

## Install MarkItDown

Full optional deps (same as upstream “backward compatible” install):

```bash
python -m pip install -U pip
python -m pip install 'markitdown[all]'
```

Smaller install (only these converters):

```bash
python -m pip install 'markitdown[pdf,docx,pptx,xlsx,xls]'
```

## Convert to Markdown

Resolve the real input path first when names contain Chinese or other non-ASCII
characters: use `list_dir` / `glob`, then pass that exact path (see skill
`unicode-paths`). Prefer quoting in shell; on Windows avoid raw `cmd` with the
default GBK console for CJK paths.

Run from the workspace (paths relative to workspace as needed):

```bash
markitdown path/to/file.pdf -o path/to/file.md
markitdown report.docx -o report.md
markitdown data.xlsx -o data.md
markitdown deck.pptx -o deck.md
```

Equivalent:

```bash
python -m markitdown path/to/file.pdf -o path/to/file.md
```

Then open the `.md` with `read_file`, or chunk/search for very large outputs.

## After conversion

1. Skim the `.md` for garbled tables or empty pages (scanned PDFs may need OCR or other tools — see `pdf` skill).
2. Use the Markdown as the basis for summarization, Q&A, or structured extraction. This skill is for **text pipeline into the model**, not pixel-perfect layout.

## References

- Upstream: [microsoft/markitdown](https://github.com/microsoft/markitdown) — optional extras (`[all]`, `[pdf]`, `[docx]`, `[pptx]`, `[xlsx]`, `[xls]`, …).
- Workspace venv behavior: `workspace/AGENTS.md`, `tools/exec` in dipper-bot.

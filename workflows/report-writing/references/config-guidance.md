# Report Writing Configuration Guidance (Level 3, loaded on demand)

Read this file when the user hits output limits or context limits during a long
report, or asks about performance. These are **user settings** (`worker.json`
under `agents`), read from the settings UI — the workflow itself never writes
config. Changes affect the whole workspace, so only suggest them; let the user
apply them.

## Output budget (`agents.maxTokens`, default 8192)

The workflow already bounds each draft to one chapter, so the default is enough
for most reports. Raise it (e.g. 16384–32768) only when the model supports
larger completions **and** the user wants fewer, longer chapters. Otherwise keep
chapters sized to fit the default budget and use `edit_file` to extend long
chapters in chunks — that works regardless of the setting.

## Context recall (`agents.recentTurnsKept`, default 2; `agents.embeddingTopK`, default 6)

For report sessions the outline + glossary are persisted on disk, so these
settings matter less than for normal chat. When a report spans very many turns
and the user wants the agent to recall earlier discussion more strongly:

- Raise `recentTurnsKept` (e.g. 3–5) to keep more recent rounds verbatim.
- Raise `embeddingTopK` (e.g. 8–12) to retrieve more older related history.

Both are clamped to 0–20 and normalized on load; `0` disables the layer.

## Model selection

Long reports benefit from a model with a large context window and strong
instruction following. If the primary model truncates or drifts, suggest adding
a stronger fallback in the model selection settings rather than changing the
workflow.

## When NOT to change config

- If a single chapter exceeds the output budget, **chunk the chapter**, do not
  just raise `maxTokens`.
- If context fills up mid-turn, the workflow's own discipline (outline in
  context, chapters on disk, grep/read on demand) fixes it; do not raise limits
  as a workaround for loading whole chapters into context.

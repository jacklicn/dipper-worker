---
name: clawhub
description: Search and install agent skills from ClawHub, the public skill registry.
homepage: https://clawhub.ai
metadata: {"dipper-bot":{"emoji":"🐕"}}
---

# ClawHub

Public skill registry for AI agents. Search by natural language (vector search).

## When to use

Use this skill when the user asks any of:
- "find a skill for …"
- "search for skills"
- "install a skill"
- "what skills are available?"
- "update my skills"

## dipper-bot workspace

dipper-bot loads skills from `{workspace}/skills/`, where each skill is a subdirectory containing `SKILL.md`. SkillsLoader reads from `workspace/skills/` first; workspace skills override built-in ones.

**Resolving workspace path**:
- Default: `~/.dipper-bot/workspace`
- Read `agents.workspace` from `~/.dipper-bot/config.json`
- If the user runs with `--workspace PATH` or sets `DIPPER_WORKSPACE`, use that path
- Before install, use `read_file` to read `~/.dipper-bot/config.json` or `config.json` in the workspace and use `agents.workspace` as `--workdir`

**`--workdir`** must be the **workspace root** (the parent of `skills/`). After install, the skill appears at `{workdir}/skills/<slug>/`.

## Search

```bash
npx --yes clawhub@latest search "web scraping" --limit 5
```

## Install

```bash
npx --yes clawhub@latest install <slug> --workdir <WORKSPACE_ROOT>
```

- `<slug>`: skill name from search results
- `<WORKSPACE_ROOT>`: workspace root path. Use `~/.dipper-bot/workspace` if unknown; otherwise read from config
- Always include `--workdir`; without it, skills install to the current directory instead of the workspace

## Update

```bash
npx --yes clawhub@latest update --all --workdir <WORKSPACE_ROOT>
```

## List installed

```bash
npx --yes clawhub@latest list --workdir <WORKSPACE_ROOT>
```

Or use `list_dir` to inspect subdirectories under `{workspace}/skills/`.

## Notes

- Requires Node.js (`npx` comes with it).
- No API key needed for search and install; publish requires `npx --yes clawhub@latest login`.
- `--workdir` must point to the workspace root; without it, skills install to the current directory and dipper-bot will not load them.
- After install, remind the user to start a new session to load the skill.

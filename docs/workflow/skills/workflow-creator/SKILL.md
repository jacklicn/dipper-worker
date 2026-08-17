---
name: workflow-creator
description: >-
  Guide for creating high-quality reusable Workflows (WORKFLOW.md) for Dipper Agent.
  Use when the user wants to create a new workflow, turn a multi-step procedure into a
  reusable flow, capture a task process as mermaid steps, or edit/improve an existing
  workflow.
version: 1
---
# Creating a Workflow

A Workflow is a reusable process unit that translates "what the user wants to do" into "what to do first, what next, which tool each step uses, and what it produces". This skill guides you from the user's requirements to a `WORKFLOW.md` that conforms to the `docs/workflow/index.md` specification.

Read the specification before creating: `docs/workflow/index.md` (three-level progressive disclosure, graph-step one-to-one correspondence, process rules, tool-call conventions).

## When to Use

- The user asks to "create a workflow / process / standardized flow"
- The user describes a multi-step task they want solidified into an automatically executed flow
- The user asks to modify or improve an existing workflow
- The user did something reusable and multi-step in the session and says "solidify this flow"

## Creation Process

### Phase 1: Understand the Intent

Interview first; don't rush to write files:

1. **What task does it solve**? Give the task class a name (e.g. "code review", "release notes").
2. **Trigger scenario**: when will the user use it? Collect trigger words (Chinese + English).
3. **Inputs and outputs**: what inputs are needed (files/directories/strings)? What is produced (files/reports)?
4. **Existing steps**: does the user already have a habitual flow? Extract tool-call sequences, corrections, and input/output formats from the session history.
5. **Boundaries and rules**: what must not be done? Where do artifacts go? How are failures handled?

Fill in missing information with `ask_user` before moving to the next phase.

### Phase 2: Design the Flowchart

Draw the execution flow with mermaid, **following the graph-step correspondence rule** (spec 5.2.1):

- Every node must have a matching step section; every step must appear once in the graph
- Node names exactly match step names and are globally unique (the `step-N` prefix need not appear in nodes)
- Decision nodes use diamonds `{}`, must also have a step section, and use `Branch` to state where each branch goes
- Parallel steps (scatter) are one node in the graph
- The graph must be complete: start, branches, end

Show the graph to the user for confirmation before writing the steps.

### Phase 3: Write the WORKFLOW.md

Create the directory and files under `<workspace>/workflows/<name>/`:

1. **frontmatter** (Level 1 metadata):
   - `name`: kebab-case, matching the directory name, lowercase letters/digits/hyphens only
   - `description`: function + usage timing + trigger words (Chinese and English), determines the trigger rate
   - `inputs` / `outputs`: declare explicitly, mark required
   - `version` / `tags`: optional
2. **Overview**: one paragraph stating what it does, when to use it, and what it produces
3. **Flowchart**: the mermaid graph consistent with Phase 2
4. **Steps**: one `### <id>: <name>` section per step, with attributes: `Tools` / `Input` / `Depends on` / `Action` / `Check` (decision nodes add `Branch`, optional `when`)
5. **Process Rules**: order constraints, data dependencies, validation gates, side-effect constraints, final-state check
6. **Tool Call Conventions**: prefer builtin tools, scripts as fallback, read more write less, path conventions

> Progressive disclosure: put long docs and tables in `references/`, deterministic logic in `scripts/`, templates and data in `assets/`, keep the body lean (<500 lines).

### Phase 4: Self-Check and Validate

After writing, check against the spec:

- Graph-step one-to-one correspondence: no "orphan" nodes in the graph, no "orphan" steps in the sections
- Node names unique and matching step names
- Every step has a concrete, decidable `Check` (e.g. "file exists and is non-empty", not "confirm success")
- Tool names are precise (`read_file` / `exec`, not "view the file")
- `inputs` / `outputs` consistent with the step references
- Rules cover failure handling (retry / rollback / ask the user)
- frontmatter `description` includes function and trigger words

Use `workflow_list` to confirm the new workflow is discovered, and `workflow_get <name>` to verify it is readable.

### Phase 5: Deliver

Tell the user:

- The workflow name and path
- The trigger scenario (what phrasing triggers it)
- A flow overview (how many steps, decisions/parallelism)
- Optional: suggest 2-3 real test requests to verify it works

## Modifying an Existing Workflow

- Read the current content with `workflow_get <name>` first
- Keep the `name` in the frontmatter and the directory name unchanged
- Follow the same spec for changes; run the Phase 4 self-check after editing

## Notes

- **Only write to the workspace `workflows/`**, never modify builtin read-only workflows; a same-named workspace workflow overrides the builtin
- One workflow solves one class of task; don't pile up unrelated flows
- Keep steps to 3–8; split or reference a sub-flow beyond that
- Never write malicious or misleading instructions; rules must be auditable

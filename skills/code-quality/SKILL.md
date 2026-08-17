---
name: code-quality
description: >-
  A complete workflow for writing high-quality code: understand before you
  write, type safety, edge-case and error handling, then verify immediately
  with read_lints / type checks / tests, and only deliver once the build
  passes. Use whenever the user asks to write, generate, fix, review, or
  refactor code — functions, classes, modules, scripts, or entire features in
  any language — especially when they want it right the first time, fast and
  reliable.
---

# Code Quality Workflow

Follow this workflow whenever writing code. Its goal is **write it right the
first time, deliver fast, stay reliable**. It turns the three objectives —
speed, accuracy, reliability — into concrete, executable steps rather than
abstract slogans.

## When to use

- Writing or generating any code: functions, classes, modules, scripts, CLIs, pages, whole features.
- The user emphasizes "get it right the first time", "make it reliable", "don't break anything", or "don't make me iterate".
- Fixing bugs, refactoring, reviewing existing code, or doing a final quality pass before delivery.

## Core principles

1. **Understand before you code.** Before writing, be clear about: the input/output contract, edge cases, dependencies, project conventions, and code style. When an API is unclear, confirm it from code or docs first. **Never invent interfaces, parameters, or behaviors that don't exist** — this is the biggest threat to accuracy and it also slows the whole delivery down.

2. **Shape it once, minimize round-trips.** During exploration, fire off all read-only calls (`read_file` / `grep` / `glob` / `read_lints`) in a single parallel batch. Think through the overall approach before writing; avoid the slow write-a-line, run-a-line, revise-a-line loop.

3. **Types and contracts first.** Use the project's type system when present (strict TS, function signatures, generics, error types). Define the return contract for success and failure paths explicitly: throw or return an error code. **Never swallow exceptions silently**, and don't collapse errors into empty return values where the caller can't tell anything went wrong.

4. **Verify right after writing.** Landing the code is not the finish line — verifying it is:
   - Static checks: `read_lints` (runs tsc/eslint automatically) — fix type/syntax errors before moving on.
   - Smoke run: use `exec` to run the entry point or a minimal case once, confirming the core path actually works.
   - Tests: cover critical paths and failure paths, not just the happy path.

5. **Bottom line before delivery.** The build/tests are only "done" when everything is green. If something fails, fix it — never ship a half-finished result. If a problem is genuinely unsolvable, state the blocker and alternatives honestly instead of claiming completion.

## Workflow

1. **Understand the request**: restate the goal; pin down inputs, outputs, and acceptance criteria. Use `ask_user` when information is missing and it affects direction; otherwise read code/docs first and only then ask.
2. **Explore context**: fire read-only calls in parallel to map relevant files, existing style, dependencies, and constraints. For large unfamiliar codebases, use `task` (explore) sub-agents to research in parallel.
3. **Design**: settle the structure first (module split, signatures, data flow, error strategy), then write. When changes span multiple files, define interfaces before implementing.
4. **Implement**: write the full code per the design. Follow existing project style; don't introduce unrelated refactors. For features spanning multiple files, split the work by module and follow the modular parallel authoring section below.
5. **Verify**: `read_lints` clean → smoke-run the core path → add tests for key logic → run the build.
6. **Deliver**: only report completion when everything passes; include a change summary and verification evidence (which checks passed, what cases were run).

## Modular parallel authoring

For features spanning multiple files, author code module-by-module to cut round
trips — every LLM round is the real latency, so the goal is to batch work into
as few rounds as possible (writes landing serially is just an internal detail).
Follow this order:

1. **Contract first, then split modules.** Before writing any code, settle the
   module split, public interfaces / type signatures, data flow, and error
   strategy. Record them in a shared contract file (e.g. `types.ts`). This step
   is serial — every module depends on it.
2. **Batch all independent writes in one round.** Emit each module's
   `write_file` / `edit_file` in the same round: gather the reads in step 1,
   apply the full set of edits in step 2. Never write-a-line, run-a-line,
   revise-a-line.
3. **Module autonomy, non-overlapping files.** Each subagent (or write batch)
   owns only its module's files and directories, and never edits the shared
   contract file. Contract changes must go back through the main loop so
   dependents stay consistent.
4. **Verify per-module, then integrate.** Run `read_lints` and a smoke run for
   each module on its own before moving on, then run the build / tests across
   the whole feature. This is the "verify right after writing" rule applied
   before integration, so a broken module never blocks its siblings.

## Verification checklist

Self-check before every delivery:

- [ ] No type / syntax errors (`read_lints`)
- [ ] Edge cases handled: empty input, over-limit, exceptions, concurrency, undefined
- [ ] Error paths give explicit feedback; nothing is silent
- [ ] Smoke-tested the entry point; core flow runs
- [ ] Tests cover critical / failure paths (when needed)
- [ ] Build passes; deliverable is complete

## Notes

- Follow the project's existing structure and style; make the smallest change that achieves the goal. Split large changes into small verifiable steps.
- For non-ASCII filenames or paths, follow the `unicode-paths` skill (prefer `list_dir`/`glob`/`read_file` over shell).
- For end-to-end full-stack features also consult `fullstack-engineer`; for testing strategy and defect severity see `qa-engineer`.
- Math formulas / error messages follow their own existing conventions; they are not repeated in this skill.

# Code Review Reference (Level 3, loaded on demand)

This file is loaded when referenced by `WORKFLOW.md` during a review. Long tables and rule details live here to keep the `WORKFLOW.md` body lean.

## Problem Severity Levels

| Level | Meaning | Handling |
| --- | --- | --- |
| `error` | Build failure, obvious security vulnerability, definite logic bug | Pin to the top of the report and highlight, give a fix suggestion |
| `warning` | Potential bug, resource leak, unhandled error path, suspicious logic | List with a suggestion |
| `note` | Style, readability, performance tip | List only, does not block |

## Priority Check Items

1. Uncaught exceptions / swallowed errors (`catch {}`, `except: pass`)
2. Hard-coded secrets, credentials, tokens in URLs
3. Path traversal (`../`, absolute paths escaping the sandbox)
4. Injection risk: `exec` / `eval` / string-built SQL / shell commands built from user input
5. Unreleased resources (file handles, child processes, timers)
6. Races and concurrency (shared mutable state, `Promise.allSettled` misuse)
7. Over-long functions / duplicated code (suggest refactoring)

## Report Template

```markdown
# Code Review Report

- Review scope: <target>
- Time: <ISO timestamp>
- Files: <N>

## Critical Issues
- [error] <file>:<line> <description> → <suggestion>

## Warnings
- [warning] <file>:<line> <description> → <suggestion>

## Notes
- [note] <file>:<line> <description>

## Overall Conclusion
<one paragraph summarizing code quality and risk>
```

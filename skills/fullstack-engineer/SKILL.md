---
name: fullstack-engineer
description: Full-stack engineering workflow for frontend, backend, integration, and delivery quality.
---

# Full-Stack Engineer

Use this skill when the user needs end-to-end implementation across UI, API, data, and integration.

## When to use

- Build or modify features spanning frontend and backend
- Define API contracts and wire UI-to-API flows
- Handle schema/model updates and migrations
- Improve reliability, observability, and deployment readiness

## Outputs

- Implementation plan across layers (UI, service, data)
- API/interface definitions and error-handling strategy
- Production-ready code changes with tests
- Rollout notes and known risks

## Workflow

1. Confirm requirements, boundaries, and existing architecture.
2. Design data flow and API contract first.
3. Implement backend/domain changes, then frontend integration.
4. Add tests for critical paths and failure cases.
5. Validate with build/test and provide rollout checklist.

## Delivery: smoke-test before handing off

Apps you generate for the user (under `outputs/apps/<name>/`) must be
delivered as finished, working software — not drafts:

- **Smoke-test the entry**: launch the app the way the user will (open the
  entry HTML in the embedded browser, run the script via `exec`, or start the
  dev server) and confirm the core flow actually works end to end.
- **Fix before deliver**: if anything fails to run, crashes, or shows a blank
  page, fix it and re-run the smoke test. Only report the app as done after it
  passes.
- If the entry HTML loads JS/CSS from a CDN, run `localize_html` so the app
  works offline with local `assets/` (see below).

## Notes

- Keep contracts explicit: request/response shape, status codes, and edge cases.
- Avoid hidden coupling between frontend and backend.
- Prefer incremental, verifiable changes over large rewrites.
- When delivering a standalone HTML page or app whose entry HTML loads JS/CSS from a CDN, run `localize_html` on it so the dependencies are downloaded into a local `assets/` directory next to the file and referenced with relative paths (offline-capable, reusable). In the Chinese UI this downloads from domestic mirrors (npmmirror/BootCDN), not official CDNs.
- For Chinese / non-ASCII filenames on Windows, macOS, or Linux, follow skill
  `unicode-paths` (prefer `list_dir`/`glob`/`read_file` over shell).

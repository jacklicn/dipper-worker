# Dipper Worker

> Desktop AI Worker · AI collaboration assistant
>
> Simple, efficient, reliable, economical.

Dipper Worker is a desktop AI collaboration assistant. Through conversation you can handle file operations, code execution, web retrieval, browser automation, image text recognition, document generation, and more, plus built-in browser, terminal, screenshot, bookmarks, and other desktop collaboration features.

Chinese: [README_ZH_CN.md](./README_ZH_CN.md).

## Features

- **Simple**: Add a workspace → fill in API Base / Key / Model → start chatting. Built-in catalog of 20 major model providers (DeepSeek, Zhipu, Tongyi Qianwen, Doubao, Kimi, Google, OpenAI, Anthropic, xAI, etc.); one-click select and auto-fetch model lists.
- **Efficient**: Agent worker dispatches built-in tool packs (+ optional workspace plugins and MCP); after each turn, background learning deposits memory and reusable skills—smoother over time; explore subagents run in parallel by CPU core count.
- **Reliable**: Keys encrypted via OS secure storage (safeStorage); permission gates + authorized folders + path guards + network guards (SSRF protection); sessions persisted locally.
- **Economical**: Pure local desktop app—no subscription, no middleman service; ships with China mirrors for packaging, ready out of the box. Conversations automatically conserve tokens: oldest messages are trimmed to context budget before send, long sessions auto-compact with summaries, avoiding oversized context driving up per-request cost.

## Desktop collaboration

- **Built-in browser**: Multi-tab, back/forward/refresh, bookmarks (library + floating overlay), browsing-data cleanup, browser fingerprint isolation, open local HTML / images.
- **Built-in terminal**: Default cwd is the current workspace; create / restart / end sessions.
- **File panel**: Browse the workspace tree; quick open / reveal in folder / download.
- **Screenshot**: Global hotkey; annotate (rectangle / arrow / text / brush), color picker.
- **System tray**: Closing the window keeps the app in the tray for quick restore; single-instance lock.
- **Session management**: Groups, drag-and-drop, pin, archive, search, rename, context compaction.
- **Settings**: AI providers, Agent parameters, permissions & authorized folders, shortcuts, appearance (theme / layout / font scale).
- **Chinese / English UI**: Language auto-detected; switch anytime.

## Self-learning

After each turn, background silent deposition:

- User preferences & habits → `memory/USER.md`
- Project facts / decisions → searchable memory notes
- Reusable experience → `skills/*/SKILL.md` (auto-loaded by the agent next time)
- Reusable flows → `workflows/*/WORKFLOW.md` (mermaid orchestration + steps + rules; agent follows the flow)

Low-confidence results are discarded automatically; logs go to `.dipper-worker/learning.jsonl` and do not interrupt by default.

## Workspace

- **Single workspace**: Sidebar `+` to add or switch directories; rename, change color / icon, open folder, remove (clears registration only, does not delete disk).
- **Global config (includes secrets)**: `~/.dipper-worker/worker.json` — Provider / API Key / Model / MCP / Agent params, workspace registry.
  - Optional `retention` block controls cleanup (built-in defaults if omitted): `maxUserMemoryBullets`, `maxMemoryNotes`, `toolResultRetentionMs`, `learningLogRetentionMs` / `learningLogPruneMinSize` / `learningLogPruneIntervalMs`.
- **Inside workspace (no secrets)**: `sessions/`, `memory/`, `skills/`, `workflows/`, `uploads/`, `downloads/`, `outputs/`, `plugins/`; groups / permissions / authorized dirs / appearance profiles under `<workspace>/.dipper-worker/`.
- **Workspace plugins**: install packs at `<workspace>/plugins/<pack>/` (`manifest.json` + entry). External packs share one plugin-host child process and one **workspace trust domain** (packs are not isolated from each other). Loaded on workspace start; **hot-reloaded** when files change (idle; selective by kind). `reloadWorkspace()` forces a full refresh. Trusted local code; cannot override builtin pack ids or tool names. Sample: `examples/plugins/echo-pack/`.
- **Security**: API keys live only in OS secure storage (`secrets.json`, safeStorage encrypted); `getConfig` is redacted before return; plaintext keys only via the dedicated `reveal-api-key` channel after in-app confirmation.

## Architecture

Microkernel-style split: shared `@dipper/*` packages; Electron is one product host among others.

```text
┌─ Desktop product ────────────────────────────────────────────┐
│  Renderer (React)                                            │
│       │  IPC · RENDERER_AGENT_INVOKE_METHODS                 │
│       ▼                                                      │
│  Electron Main                                               │
│    AgentBridge · browser / terminal / screenshot / tray      │
│    @dipper/host-desktop  (CAP_BROWSER · CAP_SECRETS)         │
│       │  DuplexTransport                                     │
│       │  call / call-res / event / ready{caps,packs}         │
│       │  host-req → cap.invoke only                          │
│       ▼                                                      │
│  UtilityProcess · worker/agent/agent-host                    │
└──────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─ @dipper/agent ──────────────────────────────────────────────┐
│  LocalAgentRuntime · turn loop · sessions · RPC facades      │
│  ├── Tool packs: builtin + workspace/plugins                 │
│  ├── MCP · PermissionGate · QuestionGate                     │
│  └── Learning (memory / skills / workflows)                  │
│       Cap bus (remote → host)                                │
└──────────────────────────────────────────────────────────────┘
   @dipper/kernel                 @dipper/protocol
   CapRegistry · transports       Capability / pack IDs
   PluginRegistry · disk loader   ops · plugin manifests

┌─ Library hosts · worker/hosts/cli ───────────────────────────┐
│  embedded (in-process)  │  child_process → child-host        │
│  @dipper/host-cli       │  KERNEL_INVOKE_METHODS only        │
└──────────────────────────────────────────────────────────────┘
```

| Package | Role |
|---------|------|
| `@dipper/protocol` | Capability / pack IDs, ops, plugin contracts |
| `@dipper/kernel` | CapRegistry, transports, PluginRegistry, disk pack loader |
| `@dipper/agent` | Runtime, sessions, tools, packs, runners, Kernel/Product/Renderer facades |
| `@dipper/host-desktop` | Desktop browser + OS secrets capabilities |
| `@dipper/host-cli` | File/env secrets (no browser) |

## Project layout

```text
dipper-worker/
├── packages/          # @dipper/* workspace packages
│   ├── protocol/
│   ├── kernel/
│   ├── agent/
│   ├── host-desktop/
│   └── host-cli/
├── worker/            # Electron main / preload / IPC / desktop adapters
│   ├── agent/         # agent-bridge, agent-host, child-host, desktop browser tools
│   └── hosts/cli/     # embedded / child library hosts
├── src/               # React UI (chat / sidebar / panel / settings / screenshot)
├── shared/            # Types re-exported for the renderer
├── examples/plugins/  # Sample workspace tool packs
├── scripts/           # electron-dev / dist / clean / rasterize-icon
├── resources/         # Icons
├── skills/            # Bundled skills
└── docs/              # PACKAGE / PROTOCOL / MODEL-DATA / PLUGINS / workflow
```

## Development environment

- Node.js >= 20
- pnpm 11+

## Quick start

```bash
cd dipper-worker
pnpm install
pnpm dev   # build packages + electron main → Vite + Electron
```

## Scripts

| Command | Description |
|------|------|
| `pnpm dev` | Compile packages/main + Vite + Electron dev run |
| `pnpm build` | Clean dist → build renderer + electron (includes `build:packages`) |
| `pnpm build:packages` | Clean and build `@dipper/*` packages |
| `pnpm typecheck` | Build packages + TypeScript check |
| `pnpm icon:rasterize` | Generate platform icons from SVG |
| `pnpm dist` | Icons + build + package for current environment |
| `pnpm dist:win` | Windows x64: portable + NSIS |
| `pnpm dist:mac` | macOS arm64: dmg + zip |
| `pnpm dist:linux` | Linux x64: AppImage |
| `pnpm dist:protected:*` | Obfuscate electron side, then package (raise reverse-engineering bar) |

Packaging: [docs/PACKAGE.md](./docs/PACKAGE.md). App↔model data: [docs/MODEL-DATA.md](./docs/MODEL-DATA.md). Wire protocol: [docs/PROTOCOL.md](./docs/PROTOCOL.md). Workspace plugins: [docs/PLUGINS.md](./docs/PLUGINS.md).

## License

Dipper Worker is open source under the [MIT License](./LICENSE).

Copyright © 2026 Dipper. All rights reserved.

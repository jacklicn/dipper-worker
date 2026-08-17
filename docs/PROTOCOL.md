# Dipper AI Worker Protocol Reference

This document describes the communication protocols between roles in Dipper Worker. It covers three interaction boundaries: **inter-process** (Renderer ↔ Electron Main IPC, Main ↔ Agent Worker UtilityProcess RPC), **app ↔ model** (OpenAI-compatible HTTP between Agent and LLM providers, and the bidirectional contract for skills/tools), and **app ↔ external services** (Agent ↔ MCP Server via stdio / Streamable HTTP / SSE JSON-RPC). Each chapter includes message formats, channel conventions, call semantics, and full examples for development and troubleshooting.


## 1. Architecture overview

The app has three process layers; the protocol differs at each boundary:

```
┌──────────────────────┐
│    Renderer (React)  │ ◀── contextBridge ──▶ Electron IPC
└──────────────────────┘
           │  ipcRenderer.invoke / ipcRenderer.on
           ▼
┌──────────────────────┐
│    Main (Electron)   │ ◀── UtilityProcess ──▶ RPC
└──────────────────────┘
           │  ↓ call · host-res
           │  ↑ call-res · event · host-req
           ▼
┌──────────────────────┐
│   Agent Worker       │
│  (UtilityProcess)    │
└──────────────────────┘
           │
           ├──▶ LLM Provider    HTTP (OpenAI-compatible)
           ├──▶ MCP Server      JSON-RPC 2.0 (stdio / HTTP / SSE)
           └──▶ Child processes exec / scripts / node / python
```

> ↓ / ↑ indicate message direction; ◀── ──▶ on the right are channels; bottom are Agent-owned external dependencies.

| Boundary | Transport | Message format |
|------|----------|----------|
| Renderer → Main | Electron IPC (`ipcRenderer.invoke`) | Request/response; channels `agent:*`, `workspaces:*`, `browser:*`, etc. |
| Main → Renderer | Electron IPC (`webContents.send`) | One-way push events; channels `agent:chat-event`, `agent:status-changed`, etc. |
| Main → Agent Worker | `utilityProcess` + `parentPort` | JSON: `call` / `call-res` / `event` / `host-req` / `host-res` |
| Agent → LLM | HTTP (OpenAI-compatible / custom) | JSON, `messages` + `tools` |
| Agent → MCP Server | stdio / Streamable HTTP / SSE | JSON-RPC 2.0 |

## 2. Renderer ↔ Main: Electron IPC

### 2.1 Request / response (invoke / handle)

The renderer calls the main process via `window.dipper` exposed by `preload.ts` (type `DipperWorkerAPI`, defined in `worker/types.ts`). Each method maps to an IPC channel.

- **Request**: `ipcRenderer.invoke(channel, ...args)`
- **Response**: Promise value from `ipcMain.handle(channel, handler)`
- Channel names use `:`-separated namespace prefixes: `agent:`, `workspaces:`, `browser:`, `terminal:`, `shell:`, `fs:`, `window:`, `screenshot:`, `bookmarks:`, `shortcuts:`, `prefs:`, `clipboard:`

**Example**: list sessions

```typescript
// preload.ts
listSessions: (offset, limit) => ipcRenderer.invoke('agent:sessions', offset ?? 0, limit ?? 30),
```

```typescript
// worker/ipc/agent-ipc.ts
ipcMain.handle('agent:sessions', (_e, offset, limit) =>
  ctx.runtime.invoke('listSessions', [offset, limit]),
)
```

### 2.2 One-way push (on / send)

Main pushes events to the renderer; the renderer subscribes:

- `ipcMain` side: `webContents.send(channel, payload)`
- `preload` side: `ipcRenderer.on(channel, cb)` and return an unsubscribe function

**Example**: chat stream events

```typescript
// worker/main.ts — broadcast
function broadcastChatEvent(event: ChatStreamEvent): void {
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('agent:chat-event', event)
  }
}

// worker/preload.ts — subscribe (returns unsubscribe)
onChatEvent: (cb) => {
  const listener = (_event: Electron.IpcRendererEvent, ev: ChatStreamEvent) => cb(ev)
  ipcRenderer.on('agent:chat-event', listener)
  return () => ipcRenderer.removeListener('agent:chat-event', listener)
},
```

### 2.3 Security boundary

- Renderer uses `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true` (`worker/main.ts`).
- Only methods explicitly exposed by `preload.ts` can reach main.
- The `agent:invoke` channel (`worker/ipc/agent-ipc.ts`) only allows the `RENDERER_AGENT_INVOKE_METHODS` whitelist (`@dipper/agent` `facade/renderer`), preventing XSS from retargeting the workspace or triggering lifecycle operations.

## 3. Main ↔ Agent Worker: UtilityProcess RPC

The Agent lives in an Electron `utilityProcess` (script `agent-host.js`) and talks to main’s `AgentBridge` via `process.parentPort`. Messages are JSON objects with a `type` discriminant. Message types and allowlists live in `@dipper/agent` (`host-protocol` / `facade`); desktop entry is `worker/agent/agent-host.ts`.

### 3.1 Message types

```typescript
/** Main → Agent Worker */
type HostToAgentMessage =
  | { type: 'call'; id: string; method: keyof AgentRuntimeApi; args: unknown[] }
  | { type: 'host-res'; id: string; ok: true; result: unknown }
  | { type: 'host-res'; id: string; ok: false; error: string }

/** Agent Worker → Main */
type AgentToHostMessage =
  | {
      type: 'ready'
      protocol?: 1
      capabilities?: string[]
      packs?: string[]
    }
  | { type: 'call-res'; id: string; ok: true; result: unknown }
  | { type: 'call-res'; id: string; ok: false; error: string }
  | { type: 'event'; event: 'status'; status: AgentStatus }
  | { type: 'event'; event: 'chat'; payload: ChatStreamEvent }
  | { type: 'event'; event: 'bot-status'; status: AgentDetailStatus }
  | { type: 'host-req'; id: string; method: string; args: unknown[] }
```

`ready` carries negotiation: `capabilities` (e.g. `browser`, `secrets`) and active `packs` (including workspace external packs).

### 3.2 Call semantics (request / response)

- Main sends `{ type: 'call', id, method, args }` (see `invokeOnce` in `agent-bridge.ts`).
- Agent replies with `{ type: 'call-res', id, ok, result | error }`.
- `id` is `c-<timestamp>-<seq>`; main’s `pending` Map matches Promises by id.
- Method names must be members of `AgentRuntimeApi` (`@dipper/agent`); the desktop UtilityProcess uses `AGENT_INVOKE_METHODS` (Kernel ∪ Product), while `child-host` allows only `KERNEL_INVOKE_METHODS`.
- `AgentBridge.invoke` is type-safe: method name / arg tuple / return type are inferred from `AgentRuntimeApi`; if the worker dies between calls, it auto-restarts and retries once.

**Example**: main calls `listSessions`

```typescript
// AgentBridge side
this.postToChild({ type: 'call', id: `c-${Date.now()}-${++this.seq}`, method: 'listSessions', args: [0, 30] })

// agent-host.js receives
// → validate ALLOWED → dispatch('listSessions', [0, 30])
// → reply { type: 'call-res', id, ok: true, result: { sessions: [...], hasMore: true } }
```

### 3.3 Event push (one-way)

Agent pushes `{ type: 'event', event: 'chat' | 'status' | 'bot-status', ... }`; main’s `onChildMessage` dispatches to `AgentBridgeEvents` callbacks, then `main.ts` broadcasts to the renderer.

Chat stream events `ChatStreamEvent` (`worker/types.ts`) are the core protocol; full list:

| type | Direction | Purpose |
|------|------|------|
| `status` | agent→renderer | Session activity `idle/thinking/responding/waiting/compacting/retry/error` |
| `text.delta` | agent→renderer | Text delta (merged by `StreamCoalescer`, 32ms / 96 chars) |
| `thinking.delta` | agent→renderer | Thinking delta (same coalescing) |
| `thinking.done` | agent→renderer | Thinking block done, with `durationSec` |
| `progress` | agent→renderer | Live tool progress (e.g. download `detail`) |
| `tool.start` / `tool.end` | agent→renderer | Tool call start / end, with `toolCallId`, args, result |
| `permission.asked` | agent→renderer | Permission confirmation (`permissionId` + category) |
| `question.asked` | agent→renderer | Question (`questionId` + options) |
| `subagent.start` / `subagent.end` | agent→renderer | Subagent lifecycle |
| `compaction.started` / `compaction.ended` | agent→renderer | Session compaction |
| `retry` | agent→renderer | Provider retry info |
| `done` | agent→renderer | Turn end: `content` + `parts` + `durationSec` |
| `error` | agent→renderer | Error; `error` === `'aborted'` means local cancel |

**Example**: full conversation event sequence (correlated by `requestId`)

```jsonc
{ "requestId": "req-1", "type": "status", "activity": "thinking" }
{ "requestId": "req-1", "type": "thinking.delta", "delta": "The user wants to download an installer, " }
{ "requestId": "req-1", "type": "tool.start", "tool": "download_url", "detail": "{\"url\":\"...\",\"path\":\"downloads/app.zip\"}", "toolCallId": "call_1" }
{ "requestId": "req-1", "type": "progress", "tool": "download_url", "detail": "Downloading app.zip · 45% · 12.3 MB / 27.1 MB · 2.4 MB/s · 8 conn" }
{ "requestId": "req-1", "type": "tool.end", "tool": "download_url", "toolCallId": "call_1", "result": "Downloaded 27.1 MB\nmode: multi (8 connections)\npath: downloads/app.zip", "status": "done" }
{ "requestId": "req-1", "type": "text.delta", "delta": "Download complete; file is at " }
{ "requestId": "req-1", "type": "text.delta", "delta": "downloads/app.zip." }
{ "requestId": "req-1", "type": "done", "content": "Download complete; file is at downloads/app.zip.", "parts": [...] }
{ "requestId": "req-1", "type": "status", "activity": "idle" }
```

### 3.4 Reverse calls (host-req / host-res)

When the Agent needs host capabilities (browser, provider secrets), it sends `{ type: 'host-req', id, method, args }`. On desktop this goes through `AgentBridge` onto the **capability bus**. The wire supports **only**:

- `cap.invoke` — unified capability call (`capabilityId` + `op` + args); desktop impl is `@dipper/host-desktop` (browser / secrets)

The Agent uses a remote CapRegistry / `parentInvoke` (`@dipper/agent` `parent-rpc`) with a timeout. Browser tools go through `browser-proxy` + `CAP_BROWSER` — there is no separate `browserTool` or plaintext secret method on the wire.

**Example**:

```typescript
// Agent (worker) — via cap bus
await invokeCapability('secrets', /* op + args */)

// Wire shape (illustrative)
// host-req: { method: 'cap.invoke', args: [capabilityId, ...] }
// → main CapRegistry → host-res
```

### 3.5 Stream coalescing (StreamCoalescer)

`@dipper/agent` `stream-coalesce` only coalesces `text.delta` / `thinking.delta` (flush every 32ms or 96 chars). Other event types (`progress`, `tool.start/end`, `status`, etc.) flush any pending coalesced buffer first, then pass through, so live progress is not delayed.

## 4. Agent ↔ LLM: model provider protocol

> Field meanings, send/receive examples, local persistence, and **security/privacy** are covered in [MODEL-DATA_EN.md](./MODEL-DATA.md). This chapter focuses on transport format and call semantics.

Agent builds the primary model + fallback chain via `buildLlmProvider(cfg)` (`@dipper/agent` provider) and uses a unified `llm.chat(messages, tools, opts)` interface. Transport is HTTP JSON in OpenAI-compatible form. Core types live in `@dipper/agent`.

### 4.1 Unified interface

```typescript
// worker/agent/provider/types.ts
export type LlmProvider = {
  readonly name: string
  readonly model: string
  chat(messages: LlmMessage[], tools: ToolDef[], opts: ChatOptions): Promise<LlmResponse>
  listModels?(): Promise<string[]>
}

export type ChatOptions = {
  maxTokens: number
  temperature: number
  signal?: AbortSignal
  onTextDelta?: (delta: string) => void      // body delta → text.delta
  onThinkingDelta?: (delta: string) => void  // thinking delta → thinking.delta
  model?: string                             // fallback-chain model override
}
```

The only low-level implementation is `OpenAIProvider` (`worker/agent/provider/openai.ts`), compatible with any OpenAI-compatible endpoint; `createProviderChain` (`worker/agent/provider/fallback.ts`) handles retries and multi-provider fallback.

### 4.2 Message format (LlmMessage)

```typescript
// @dipper/agent types
export type ChatRole = 'system' | 'user' | 'assistant' | 'tool'

export type LlmMessage = {
  role: ChatRole
  content?: string
  /** OpenAI-compatible thinking continuity field (e.g. reasoning_content); omit for non-thinking models */
  reasoning_content?: string
  tool_calls?: ToolCallDef[]      // assistant-initiated tool calls
  tool_call_id?: string           // tool reply links to the call
  name?: string                   // tool name on tool reply
}

export type ToolCallDef = {
  id: string
  type: 'function'
  function: { name: string; arguments: string }  // arguments is a JSON string
}
```

### 4.3 Request format

`POST {apiBase}/chat/completions`, auth header `Authorization: Bearer <apiKey>` (omitted when no key, for local services), optional `extraHeaders`:

```jsonc
{
  "model": "gpt-4o",
  "messages": [
    { "role": "system", "content": "You are an AI assistant running on this machine…" },
    { "role": "user", "content": "Help me download the QQ installer" }
  ],
  "max_tokens": 8192,
  "temperature": 0.7,
  "stream": true,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "download_url",
        "description": "Download files over http(s), magnet, torrent, or metalink.",
        "parameters": {
          "type": "object",
          "properties": {
            "url": { "type": "string" },
            "path": { "type": "string" }
          },
          "required": ["url"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

- Without `onTextDelta`, `stream: false` (blocking); otherwise `stream: true`.
- When `tools` is empty, omit `tools` / `tool_choice`.

### 4.4 Response format (non-streaming)

```jsonc
{
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "content": "",
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "download_url",
          "arguments": "{\"url\":\"https://...\",\"path\":\"downloads/app.exe\"}"
        }
      }]
    }
  }]
}
```

Client parses into `LlmResponse` (`@dipper/agent`):

```typescript
export type LlmResponse = {
  content: string
  /** Reasoning: read message.reasoning_content or reasoning (thinking models) */
  reasoning?: string
  toolCalls: ToolCallRequest[]   // arguments already JSON.parse'd to objects
  finishReason: string           // stop | tool_calls | length | ...
}
```

### 4.5 Streaming response (SSE)

When `stream: true`, the body is SSE framed by line: `data: <json>`, ending with `data: [DONE]`. Deltas live in `choices[0].delta`:

```jsonc
data: {"choices":[{"delta":{"reasoning_content":"User wants QQ; find the official link first…"}}]}

data: {"choices":[{"delta":{"content":"Download complete,"}}]}

data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_abc123","function":{"name":"download_url","arguments":"{\"url\":"}}]}}]}

data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"https://...\"}"}}]}}]}

data: {"choices":[{"finish_reason":"tool_calls"}]}

data: [DONE]
```

Handling rules (`OpenAIProvider.chatStream`):

- `delta.content` → append body and fire `onTextDelta`
- `delta.reasoning_content` or `delta.reasoning` → append reasoning and fire `onThinkingDelta`
- `delta.tool_calls` accumulate by `index`; `name` and `arguments` are concatenated from stream chunks
- Record `finish_reason`; after the stream, assemble accumulated `tool_calls` into complete JSON and `JSON.parse`

### 4.6 Multi-turn tool-call protocol

Agent and model loop as “model proposes → app executes → results return → propose again” (`agent-loop.ts` main loop). Each iteration:

1. Call `llm.chat(messages, tools, opts)`.
2. If the response has `toolCalls`: append the assistant message (with `tool_calls`) to `messages`, execute tools, then append each result as `role: 'tool'` (linked by `tool_call_id`).
3. Loop until the response has no `toolCalls` and produces `content`.

**Full example** (second-request body, carrying first-round tool call and result):

```jsonc
{
  "model": "gpt-4o",
  "messages": [
    { "role": "system", "content": "…" },
    { "role": "user", "content": "Help me download the QQ installer" },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "download_url",
          "arguments": "{\"url\":\"https://dldir1.qq.com/qqfile/QQ.exe\",\"path\":\"downloads/QQ.exe\"}"
        }
      }]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "name": "download_url",
      "content": "Downloaded 299.3 MB\nmode: multi (16 connections)\npath: downloads/QQ.exe"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "download_url",
        "description": "Download files over http(s), magnet, torrent, or metalink.",
        "parameters": {
          "type": "object",
          "properties": {
            "url": { "type": "string" },
            "path": { "type": "string" }
          },
          "required": ["url"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

On the third turn the model returns plain text, `finishReason: 'stop'`; Agent completes the turn.

Edge cases (built into `agent-loop.ts`):

- **Thinking only, no body**: model hits `finishReason: 'length'` or only produced reasoning → Agent appends a system nudge (without re-sending `reasoning_content`, to avoid blowing context) and runs one more tool-less chat to recover body text.
- **Tool-iteration cap**: after `maxIterations` (default 1000), append a “do not call tools again” user message and do a tool-less wrap-up.
- **Context budget**: `trimMessagesToTokenBudget` trims history before send; `shrinkToolMessagesForBudget` shrinks older tool-result text after each turn.

### 4.7 Reasoning content pass-through

- Request side: historical assistant messages with `reasoning_content` are passed through (multi-turn continuity for thinking models); the field is omitted on ordinary messages so strict OpenAI endpoints do not reject.
- Response side: non-stream reads `message.reasoning_content` or `message.reasoning`; stream reads `delta.reasoning_content` or `delta.reasoning`.

### 4.8 Retry and fallback chain

`FallingBackProvider` (`worker/agent/provider/fallback.ts`):

- Primary model + several fallbacks (`cfg.agents.modelSelection`); up to 2 retries per step, backoff `800ms × 2^attempt`.
- Retryable via `isLlmRetryable`: connection-class errors (connection refused / timeout / ECONNRESET / ENOTFOUND / fetch failed / network / EOF, etc.) and HTTP `429 / 500 / 502 / 503 / 504`; `aborted` and business errors are not retried.
- On retry/switch, `onRetry` → main loop emits `ChatStreamEvent.retry` (`attempt`, `message`, `nextMs`, `provider`) to the UI and sets `status: retry`.

### 4.9 Model list

`GET {apiBase}/models` (same auth header), response `{ "data": [{ "id": "gpt-4o" }, ...] }`; client sorts and returns. Maps to renderer IPC `listModels`.

### 4.10 System prompt assembly

Each turn’s system prompt is concatenated from modules (`agent-loop.ts`); order is injection priority:

```
DEFAULT_SYSTEM (built-in persona & behavior rules)
  + systemExtra (subagent and other scenario extras)
  + parallelHint (parallel subagent capability hint)
  + learning (memory inject: user preferences / project notes)
  + skills (skill index: name + description; body via on-demand read_file)
  + workflows (workflow index)
  + safetyBlock (safety/compliance constraints)
  + mathRules (math rules)
  + osRules (OS rules)
  + langRules (language instructions)
```

Context history is also selected in three layers by `buildContextualHistory` (`worker/agent/context.ts`), then the whole set is trimmed by `trimMessagesToTokenBudget`:

| Layer | Source | Content | Config |
|----|------|------|--------|
| ① Summary | `session.summary` (from compaction) | Rolling summary of recent successful tasks, merged into the single system message (strict chat templates allow only one system) | — |
| ② Raw | Tail of session | Last `recentTurnsKept` full turns verbatim (counted by user messages, including all following replies) | `agents.recentTurnsKept` (default `2`; `0` = off) |
| ③ Retrieval | Full history (last 80 messages) | Local embedding similarity search, excluding messages already covered by ② | `agents.embeddingTopK` (default `6`; `0` = off) |

- Layers merge in chronological order; ②’s id set is also ③’s exclusion set so each message is sent once.
- Over-budget trim priority (`tokens.ts`, drop oldest non-system first): current question > summary > ② raw > ③ retrieved older messages.
- `recentTurnsKept` / `embeddingTopK` are on `WorkspaceConfig['agents']` (`@dipper/agent`), written to `worker.json`; out-of-range values (non-integer / negative / >20) normalize back to defaults (`@dipper/agent` config).

### 4.11 Session compaction and recent-task summary

Session history is never pruned for the UI (all messages kept); only “summary + raw + retrieval” controls tokens sent to the model. Compaction lives in `worker/agent/compaction.ts`:

- **Trigger**: ≥28 new messages or ≥12k new tokens since last compaction (`shouldCompact`). `session.compactedMessageCount` stores the message count at last compaction as a watermark so every turn does not re-trigger. Settings “Compact session” runs the same logic manually (`runtime.ts`).
- **Successful-task selection**: `recentSuccessfulTaskMessages` walks from the tail and collects up to 7 recent “successful tasks”—assistant messages where every tool / subagent part has `status` `done` (any `error` excludes the whole turn; pure-text replies with no task parts are also excluded), paired with the nearest preceding user request.
- **Generation**: those ≤7 tasks are formatted (≤32k chars) and the LLM produces a ≤400-word plain-text summary stored as `session.summary` with prefix `[Recent task summary]`. Unlike the old “full-conversation structured JSON topics”, the new summary only covers a rolling recent-task window with no incremental merge; early tasks roll out naturally.
- **Consumption**: `buildContextualHistory` strips `[Conversation summary]` / `[Recent task summary]` prefixes, then merges the summary body into the single system message under `[Recent task summary]`.
- **Legacy compatibility**: old `[Conversation summary]` JSON summaries are likewise stripped and entered into system; the first compaction overwrites to the new format.

## 5. Model ↔ app: Skills and tool interaction protocol

This section describes how the model discovers skills via the system-prompt skill index, and how tool calls let the app perform real work. It is the bidirectional capability contract the app offers the model.

### 5.1 Three-layer progressive skill loading

Skills use an “index → body → references” structure to balance context cost and completeness (`worker/agent/skills.ts`):

| Layer | Content | When loaded | Code |
|----|------|----------|------|
| Layer 1 · Index | Each skill’s `name` + relative path + short desc + `[+references]` marker | Injected into system prompt every turn (~700 token budget) | `loadSkillsPrompt` |
| Layer 2 · Body | Full `skills/<name>/SKILL.md` | Model `read_file` on demand | `read_file` tool |
| Layer 3 · References | Large files under `skills/<name>/references/` | When the body points to them | `read_file` tool |

Index generation rules (`listSkills`):

- Workspace `skills/` wins; built-in skills with the same name are not listed twice; at startup `seedBuiltinSkills` seeds built-ins into the workspace.
- Each skill’s blurb comes from `SKILL.md` frontmatter `description` (truncated to 120 chars), else the first body line.
- Sorted by match to the user query: name hit +5, name fragment +2, blurb token +1; top 4 high matches include full blurb, others list path only.
- Directory name / frontmatter `name` mismatch or schema failure warns in startup logs (`skill-schema.ts`).

**SKILL.md spec** (`skill-schema.ts` enforces; allowed keys: `name`, `description`, `license`, `homepage`, `version`, `always`, `metadata`):

```markdown
---
name: download
description: "Use for any network file download task — the default download path: installers, archives, large binaries, torrent/magnet/metalink. Triggers: download, 下载, fetch file, get installer, torrent, magnet, .torrent, metalink."
---

# Download — body: When to use / How to call / Conventions / Troubleshooting
```

**Effect after system-prompt injection** (skill index the model sees):

```
Available skills (read SKILL.md with read_file before using one; skills with references/ have extra files you may read on demand):
Likely relevant:
- download: skills/download/SKILL.md — Use for any network file download task — the default download path… [+references]
All skills:
- cron: skills/cron/SKILL.md
- …and 12 more in workspace/skills
```

### 5.2 Model skill usage flow

The model follows “discover → read → execute”; the app supports this entirely via the generic tool protocol:

1. **Discover**: system-prompt skill index lists candidates, sorted by match.
2. **Read**: when needed, model calls `read_file` on `skills/<name>/SKILL.md`; if the body points to `references/`, read those on demand.
3. **Execute**: instructions in SKILL.md ultimately become built-in tool calls (e.g. `download_url`, `exec`, `web_fetch`).

```jsonc
// Model: read download skill body
{
  "tool_calls": [{
    "id": "call_read1",
    "function": {
      "name": "read_file",
      "arguments": "{\"path\": \"skills/download/SKILL.md\"}"
    }
  }]
}

// App executes and returns
{ "role": "tool", "tool_call_id": "call_read1", "name": "read_file",
  "content": "# Download — built-in naria2 engine…\n## When to use\nUse **`download_url`** for every network file download…" }
```

### 5.3 Tool declaration protocol

App-side tools must satisfy the `Tool` contract (`@dipper/agent` `types`) to register in `ToolRegistry`:

```typescript
export type Tool = {
  name: string                       // protocol id, e.g. download_url / read_file
  description: string                // natural-language when/what for the model
  parameters: Record<string, unknown> // JSON Schema (type/properties/required)
  meta?: ToolMeta                    // parallelSafe / permission (gate)
  execute: (params, ctx) => Promise<string>  // app execution body
}
```

After registration, `listDefs()` produces OpenAI-compatible `ToolDef[]` injected into each request’s `tools` field. Subagent scenarios use `cloneWithout(exclude)` to hide some tools.

**Tool packs** (`createBuiltinRegistry`, via PluginRegistry):

| Pack | Example tools | Notes |
|------|----------|------|
| `core` | `read_file`, `write_file`, `exec`, `web_fetch`, `ask_user`, `task`, workflow_* | Filesystem / search / exec / web / interactive / workflows |
| `media` | `download_url`, `archive`, `ffmpeg` | Download and media |
| `browser` | `browser_*` (needs `CAP_BROWSER`) | Proxied to main WebContentsView + CDP |
| `content` | `install_skill`, `install_workflow` | Content install helpers |
| Workspace external | e.g. `example_echo` | `<workspace>/plugins/*/manifest.json` — see [PLUGINS.md](./PLUGINS.md) |
| MCP | `mcp__<server>__<tool>` | Dynamically mounted external MCP tools |

**Large-file I/O** (page reads + chunked writes; no one-shot whole-file transfer):

| Tool | Cap | How to use |
|------|-----|------------|
| `read_file` without `offset`/`limit` | ~2MB hard reject; else ~8KB head + continue hint | Prefer `offset` + `limit` (e.g. 200 lines); follow `next: offset=…` |
| `write_file` / `append_file` `content` | ~6KB per call | Skeleton with `write_file`, then `append_file` chunks |
| `edit_file` | ~8MB for string replace; line-range streams | Exact `old_text` or `start_line`/`end_line`; huge string edits → line-range or `exec` |

### 5.4 Full tool-call lifecycle

From model initiation to final return, this spans §4.6’s multi-turn protocol plus permission gate, progress push, and parallel scheduling:

```
Model issues tool_calls
  │
  ├─ ① Permission gate (agent-loop.ts)
  │    classifyToolPermission → need confirm?
  │    └─ permission.asked event ─→ UI dialog
  │         ← replyPermission(permissionId,
  │             once|always|reject)
  │    reject → throw and end this turn
  │
  ├─ ② Progress & start (emit)
  │    tool.start event (tool + args summary)
  │    progress event (live progress detail)
  │
  ├─ ③ Execute (registry.execute)
  │    execute(params, ctx)
  │    ctx.signal → abort
  │    ctx.onProgress(tool, detail) → progress
  │    ctx.askPermission / ctx.askUser → ask
  │
  ├─ ④ Complete/fail (emit)
  │    tool.end event (result/status/truncated)
  │    Truncation: part.result ≤4000 chars,
  │                tool.end result ≤2000 chars
  │
  └─ ⑤ Return to model (messages.push)
       { role: 'tool', tool_call_id, name,
         content: result }
```

**Permission gate** (`ToolPermissionMeta`, `@dipper/agent` types):

- Tools without `meta.permission` auto-allow.
- `classify(args, ctx)` returning `null` auto-allows; returning `{ kind, title, detail }` requires user confirmation (`alwaysConfirm: true` forces ask even under session-level “always allow”).
- Typical policy: `read_file` read-only and `parallelSafe: true`; `edit_file` auto-allow inside workspace, ask outside; `download_url` classifies magnet/torrent as P2P and forces confirm.

**Parallel scheduling**:

- Tools marked `parallelSafe` may run in parallel (`Promise.allSettled`), e.g. `read_file`, `web_fetch`.
- Non-parallel tools run serially; `task` subagents are pooled by CPU count (`mapPool`).
- Same call fingerprint repeating past a threshold triggers a “doom loop” confirmation (`doom_loop` permission).

### 5.5 End-to-end example: model uses skill + tool to download

Using “Help me download the QQ installer” to show model, app, and UI interaction:

```jsonc
// ① App assembles system prompt (with skill index), calls LLM
POST /chat/completions
{
  "model": "gpt-4o",
  "messages": [
    { "role": "system", "content": "…Available skills:\n- download: skills/download/SKILL.md — …\n- …" },
    { "role": "user", "content": "Help me download the QQ installer" }
  ],
  "tools": [ { "type": "function", "function": { "name": "download_url", … } },
              { "type": "function", "function": { "name": "read_file", … } } ],
  "tool_choice": "auto"
}

// ② Model sees download skill index, first read_file the body
→ App runs read_file, returns skill body
→ Model follows body and calls download_url
{ "tool_calls": [{
    "id": "call_dl1",
    "function": { "name": "download_url",
      "arguments": "{\"url\":\"https://dldir1.qq.com/qqfile/QQ.exe\",\"path\":\"downloads/QQ.exe\",\"connections\":8}" }
}]}

// ③ App executes: permission classify (http download → auto-allow)
//    emit tool.start + progress
{ "requestId": "req-1", "type": "tool.start", "tool": "download_url",
  "detail": "{\"url\":\"https://…\",\"path\":\"downloads/QQ.exe\",\"connections\":8}", "toolCallId": "call_dl1" }
{ "requestId": "req-1", "type": "progress", "tool": "download_url",
  "detail": "Downloading QQ.exe · 45% · 134.5 MB / 299.3 MB · 2.4 MB/s · 8 conn" }
//  …UI renders live progress bar …

// ④ Download done, emit tool.end
{ "requestId": "req-1", "type": "tool.end", "tool": "download_url", "toolCallId": "call_dl1",
  "result": "Downloaded 299.3 MB\nmode: multi (8 connections)\npath: downloads/QQ.exe",
  "status": "done" }

// ⑤ Result returned to model; model produces final reply
{ "role": "assistant", "content": "", "tool_calls": [{ "id": "call_dl1", … }] }
{ "role": "tool", "tool_call_id": "call_dl1", "name": "download_url",
  "content": "Downloaded 299.3 MB\nmode: multi (8 connections)\npath: downloads/QQ.exe" }

→ Third turn: model returns body "QQ installer downloaded to downloads/QQ.exe (299.3 MB)."
→ App emit done and persist message; UI renders full reply
```

### 5.6 Tool protocol cheat sheet

| Convention | Notes |
|------|------|
| Tool name is protocol id | `download_url`, `read_file`, `mcp__<server>__<tool>`; later same-name registration overrides |
| Description is semantics | Model picks tools from `description`; must state triggers and default paths |
| JSON Schema params | `arguments` must be valid JSON string; parse failure falls back to `{}` |
| Result return format | Plain multiline text, 1:1 `tool_call_id`; long results truncated (4000/2000 chars) |
| Permission gate | Writes / out-of-bounds ops via `permission.asked`; decision `once/always/reject` |
| Progress | `onProgress` → `progress` events stream to UI without blocking model turns |
| Abort | User abort → `stopChat` → AbortSignal → tool throws `aborted` |
| Parallel | `parallelSafe: true` tools concurrent in same turn; `task` subagents pooled by cores |

## 6. Agent ↔ MCP Server: JSON-RPC

`McpManager` (`worker/agent/mcp.ts`) implements the MCP client with three transports; protocol is JSON-RPC 2.0.

### 6.1 Transport abstraction

`McpTransport` interface (`worker/agent/mcp/types.ts`):

```typescript
interface McpTransport {
  request(method: string, params: unknown, signal?: AbortSignal): Promise<unknown>
  notify(method: string, params: unknown): void
  close(): void
}
```

### 6.2 stdio (`mcp/stdio.ts`)

- Spawn a child process; communicate on stdin/stdout.
- Framing: prefer `Content-Length` headers (MCP standard); fall back to NDJSON single lines without headers.
- On Windows, `npx` / `npm` resolve to `.cmd` automatically.

```jsonc
// → stdout (request)
{ "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {} }
// ← stdin (response)
{ "jsonrpc": "2.0", "id": 1, "result": { "tools": [...] } }
```

### 6.3 Streamable HTTP (`mcp/http.ts`)

- Single-endpoint POST, `Accept: application/json, text/event-stream`.
- Response may be plain JSON or SSE; if the server returns `Mcp-Session-Id`, subsequent requests echo it.
- Default timeout 30s.

### 6.4 Call flow

1. `prepare(workspace, servers)` caches config; skips disabled / missing-command / missing-URL servers (including built-in ignore items such as `chrome-devtools`).
2. Lazy connect: `ensureRuntimeMcpTools` triggers `connectMcpServers` on first chat and `tools/list` to fetch tools.
3. Agent invokes `mcp__<server>__<tool>` via the tool registry; underneath runs `tools/call`.
4. On config change, `rebuildRuntimeTools` rebuilds built-ins and refreshes MCP tools; unchanged config keeps existing connections to avoid reconnect storms.

## 7. Related file index

| File | Content |
|------|------|
| `packages/protocol` | Capability / pack / plugin contracts |
| `packages/kernel` | Cap bus, transports, PluginRegistry, disk loader |
| `packages/agent` | LocalAgentRuntime, tools, facades, host-protocol, runners |
| `packages/host-desktop` / `host-cli` | Host capability implementations |
| `worker/types.ts` | Desktop IPC types; some status types re-exported from `@dipper/agent` |
| `shared/types.ts` | Renderer unified import point |
| `worker/agent/agent-bridge.ts` | Main bridge (call / cap.invoke / stream coalesce) |
| `worker/agent/agent-host.ts` | UtilityProcess entry |
| `worker/agent/child-host.ts` | child_process entry (Kernel allowlist) |
| `worker/hosts/cli/` | Embedded / child library hosts |
| `worker/ipc/agent-ipc.ts` | renderer↔main agent IPC (Renderer facade) |
| `worker/preload.ts` | contextBridge exposes `window.dipper` |
| `worker/main.ts` | IPC registration, event broadcast, AgentBridge lifecycle |
| `skills/<name>/SKILL.md` | Skill definitions |
| `examples/plugins/` | Sample workspace tool packs |

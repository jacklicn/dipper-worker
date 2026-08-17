# Application–Model Interaction Data

This document describes the data exchanged between the Dipper Worker **local application** and **LLM providers**: which fields exist, where they come from, where they are sent, how they are stored locally, and security/privacy boundaries. Protocol details (HTTP paths, SSE framing, IPC channels) are in [PROTOCOL.md](./PROTOCOL.md) Chapter 4.

---

## 1. Data-flow overview

```text
User input / attachments / session history (local)
        │
        ▼
┌───────────────────┐
│  Agent assembles  │  system + summary + history + tool defs
│  context          │
└─────────┬─────────┘
          │  HTTPS (OpenAI-compatible)
          │  Authorization: Bearer <apiKey>
          ▼
┌───────────────────┐
│  LLM provider     │  User-configured apiBase (no Dipper relay)
│  endpoint         │
└─────────┬─────────┘
          │  text / thinking / tool_calls
          ▼
┌───────────────────┐
│  Local tool       │  Results returned to the model (multi-turn)
│  execution        │  → final reply written to the session
└───────────────────┘
```

Key points:

- **No cloud relay**: Chat requests go from this machine directly to your configured `apiBase`. Dipper does not host user conversation content.
- **Secrets separated from body text**: API keys are encrypted via OS `safeStorage` in `~/.dipper-worker/secrets.json`; session bodies live in the workspace local DB and are not sent in plaintext via the settings panel.
- **What reaches the model is controllable**: Summary + recent raw turns + retrieval, plus token-budget trimming, avoid uploading unbounded full history.

---

## 2. Data sent to the model (Request)

### 2.1 Payload shape


| Field           | Type             | Description                                                      |
| --------------- | ---------------- | ---------------------------------------------------------------- |
| `model`         | string           | Current primary model or per-turn override                       |
| `messages`      | `LlmMessage[]`   | System prompt + context history + this turn’s user message + (on multi-turn) tool calls and results |
| `tools`         | tool-def array   | Function schemas available this turn; omitted when empty         |
| `tool_choice`   | `"auto"`         | Fixed when tools are present                                     |
| `max_tokens`    | number           | From Agent config                                                |
| `temperature`   | number           | From Agent config                                                |
| `stream`        | boolean          | `true` for UI streaming                                          |


Auth: `Authorization: Bearer <apiKey>` (omitted when no key is configured, for local models). Some vendors use custom headers (see each vendor adapter).

### 2.2 `messages` roles and meaning


| `role`      | Content source                                              | Privacy risk                         |
| ----------- | ----------------------------------------------------------- | ------------------------------------ |
| `system`    | Built-in persona, skill/workflow **index**, memory summary, safety & language rules, recent-task summary | Medium: memory/summary may include preferences/project facts |
| `user`      | User input, attachment path notes, historical user turns    | **High**: user text and attachment refs |
| `assistant` | Historical replies; may include `tool_calls` / optional `reasoning_content` | Medium: replies and tool args may reference local paths |
| `tool`      | Local tool results (linked by `tool_call_id`)               | **High**: file snippets, command output, page text, etc. |


Types: `@dipper/agent` (`LlmMessage` / `ToolCallDef`).

### 2.3 What modules compose the system prompt

Order is injection priority (`agent-loop.ts`):

1. Default persona and behavior rules (`DEFAULT_SYSTEM`)
2. Scenario extras (e.g. subagents)
3. Parallel subagent capability hint
4. **Learning memory** (user preferences / project note summaries)
5. **Skill index** (name + description; body via on-demand `read_file`)
6. **Workflow index**
7. Safety/compliance block (if enabled)
8. Math / OS / **UI language** instructions

### 2.4 How history reaches the model (not the full DB)

The UI may keep the full session; **history sent to the model** is assembled in three layers (`buildContextualHistory`):


| Layer           | Content                                                     | Config                            |
| --------------- | ----------------------------------------------------------- | --------------------------------- |
| ① Summary       | “Recent successful tasks” summary from compaction, merged into system | Auto / manual compaction          |
| ② Recent raw    | Last `recentTurnsKept` full turns (default 2)               | `agents.recentTurnsKept`          |
| ③ Retrieval     | Local embedding-related older messages, up to `embeddingTopK` (default 6) | `agents.embeddingTopK`; `0` disables |


Before send, `trimMessagesToTokenBudget` / `shrinkToolMessagesForBudget` trim further, prioritizing the current question and the summary.

### 2.5 Data not sent to the model (kept locally)


| Data                          | Location                          | Notes                                                                 |
| ----------------------------- | --------------------------------- | --------------------------------------------------------------------- |
| API Key plaintext             | OS-encrypted `secrets.json`       | Used only in auth headers; `getConfig` returns redacted (`hasApiKey` / `apiKeyLength`) |
| Full session SQLite / rows    | Workspace `sessions/`             | Includes older messages not selected into context                     |
| Learning log                  | `.dipper-worker/learning.jsonl`   | Background sink; not injected into UI by default                      |
| Browser cookies / cache       | Electron session                  | Not uploaded with chat completions                                    |
| Oversized tool-result spill   | `outputs/tool-results/`           | Only summary or truncated text enters context                         |


---

## 3. Data returned by the model (Response)

### 3.1 Logical result (`LlmResponse`)


| Field            | Description                                    |
| ---------------- | ---------------------------------------------- |
| `content`        | User-visible body text                         |
| `reasoning`      | Reasoning-model thinking text (maps to UI `thinking`) |
| `toolCalls`      | Parsed tool name + argument objects            |
| `finishReason`   | `stop` / `tool_calls` / `length`, etc.         |


When streaming, SSE `delta.content` / `delta.reasoning_content` / `delta.tool_calls` arrive incrementally and are regrouped locally.

### 3.2 Multi-turn tool-loop round trips

```text
Model → tool_calls (intent)
App   → execute tools (after permission gate)
App   → write role:tool results back into messages
Model → propose again or final content
```

Tool results enter **later requests’** context, so local file snippets, command output, etc. may appear again in JSON sent to the provider—this is an inherent cost of Agent capabilities; see Chapter 6 privacy notes.

---

## 4. Local persistence (after model exchange)


| Location                                 | Content                                                                       |
| ---------------------------------------- | ----------------------------------------------------------------------------- |
| Session DB `messages`                    | `id` / `role` / `content` / `parts` / `timestamp` / `durationSec` / `usage`  |
| `session.summary`                        | Compaction summary (not a separate UI message)                                |
| `memory/`, `skills/`                     | Post-turn background learning (can be disabled or confidence-filtered)        |
| `uploads/` / `downloads/` / `outputs/`   | Attachments, downloads, artifacts                                             |


Message-row `timestamp` drives UI time separators; `usage` is provider-reported or estimated token usage.

---

## 5. Examples

### 5.1 First-turn request (no tool call yet)

```http
POST {apiBase}/chat/completions
Authorization: Bearer sk-***
Content-Type: application/json
```

```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "You are AI Worker …\n\n[Skills]\n- make-pdf: …\n\nCRITICAL language rules … Simplified Chinese …"
    },
    {
      "role": "user",
      "content": "Summarize outputs/notes.md in three sentences"
    }
  ],
  "max_tokens": 8192,
  "temperature": 0.7,
  "stream": true,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "Read a text file from the workspace.",
        "parameters": {
          "type": "object",
          "properties": {
            "path": { "type": "string" }
          },
          "required": ["path"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

### 5.2 Second turn: with tool results

The model first returns `tool_calls`; after local `read_file`, the app requests again:

```json
{
  "model": "deepseek-chat",
  "messages": [
    { "role": "system", "content": "…" },
    { "role": "user", "content": "Summarize outputs/notes.md in three sentences" },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "id": "call_01",
          "type": "function",
          "function": {
            "name": "read_file",
            "arguments": "{\"path\":\"outputs/notes.md\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_01",
      "name": "read_file",
      "content": "# Notes\n- Milestone A is done\n- Beta ships next week\n…"
    }
  ],
  "tools": [ /* same as previous turn */ ],
  "tool_choice": "auto",
  "stream": true
}
```

On the third turn the model returns plain-text `content`, `finish_reason: "stop"`, which is written to the session and shown to the user.

### 5.3 Streaming deltas (illustrative)

```text
data: {"choices":[{"delta":{"reasoning_content":"Read the file first, then summarize…"}}]}

data: {"choices":[{"delta":{"content":"1. "}}]}

data: {"choices":[{"delta":{"content":"Milestone A is done."}}]}

data: {"choices":[{"finish_reason":"stop"}]}

data: [DONE]
```

### 5.4 Config redaction (visible in UI, not sent to the model)

```json
{
  "providers": {
    "deepseek": {
      "apiBase": "https://api.deepseek.com",
      "model": "deepseek-chat",
      "hasApiKey": true,
      "apiKeyLength": 35,
      "apiKey": ""
    }
  }
}
```

Plaintext keys are shown only via the dedicated `reveal-api-key` channel after user confirmation, briefly.

---

## 6. Data security and privacy

### 6.1 Trust boundaries


| Boundary              | Controls                                                                 |
| --------------------- | ------------------------------------------------------------------------ |
| Renderer ↔ Main       | `contextIsolation`, no Node integration, preload allowlist, `agent:invoke` method allowlist |
| Main ↔ Agent          | UtilityProcess RPC; methods constrained by `AgentRuntimeApi` / facades (`@dipper/agent`) |
| Agent ↔ model         | Only to user-configured `apiBase`; keys never in workspace or learning artifacts |
| Agent ↔ public tools  | URLs gated by `net-guard` (reject private / metadata addresses, reduce SSRF) |
| Files & commands      | Workspace path guards, authorized folders, PermissionGate for dangerous ops |


### 6.2 Secrets and sensitive config

- API keys: **not** written plaintext to `worker.json`; after migration stored in `~/.dipper-worker/secrets.json` (prefer `safeStorage` encryption).
- `getConfig` / settings use `redactConfig`; plaintext keys are not returned.
- Workspace sessions, memory, and skills directories **do not** store provider secrets.

### 6.3 Conversation and file privacy (important)

1. **Provider-visible scope**  
   JSON sent to the model may include: user input, recent history, retrieved older messages, file snippets from tools, command output, fetched page text, memory summaries.  
   **Privacy policy for that content is determined by your chosen model provider** (logging, training, retention, etc.). Read their terms; for highly sensitive data use local/private endpoints, or avoid letting the Agent read those files.
2. **Local defaults**  
   Dipper does not collect chats via an intermediary server. Uninstalling or deleting the workspace / `~/.dipper-worker` clears corresponding local data (back up yourself if needed).
3. **Tools expand exposure**  
   Once the model calls `read_file` / `exec` / `web_fetch`, etc., results enter later model requests. Permission prompts and “restrict to workspace” reduce accidents but cannot stop authorized operations from putting content into model context.
4. **MCP / third-party skills**  
   External MCP and installed skills may access network or local resources; install only trusted sources and heed their permission prompts.
5. **Learning and memory**  
   After a turn, the background may write `memory/` and skill drafts. Low-confidence results are discarded; still periodically review `memory/USER.md` and notes, and delete entries you do not want long-term.
6. **Transport**  
   Use `https://` for `apiBase`; self-signed or cleartext HTTP only for trusted LAN local-model setups.

### 6.4 Practical user controls

- Sensitive repos: do not authorize whole-disk folders; reject high-risk commands by default.
- Compliance: choose zero-retention / enterprise endpoints, or fully offline models.
- Reduce upload surface: lower `recentTurnsKept` / `embeddingTopK`, compact sessions regularly, avoid pasting secrets into chat.
- Cleanup: use browsing-data and workspace cleanup in settings; delete unneeded `uploads/` / `outputs/`.

### 6.5 Security-related code index


| Module                                      | Role                         |
| ------------------------------------------- | ---------------------------- |
| `worker/secrets-store.ts`                   | API key encrypt/decrypt I/O  |
| `@dipper/agent` `config` → `redactConfig`   | Config redaction             |
| `@dipper/agent` `net-guard`                 | Public URL / private-net block |
| `@dipper/agent` `permissions`               | Tool permission gate         |
| `@dipper/agent` `context`                   | History selection for model  |
| `@dipper/agent` `provider/openai`           | HTTP requests & SSE parse    |


---

## 7. Related docs


| Doc                                            | Content                                              |
| ---------------------------------------------- | ---------------------------------------------------- |
| [PROTOCOL.md](./PROTOCOL.md)                   | IPC, RPC, OpenAI-compatible protocol, Skills/MCP contracts & full messages |
| [PACKAGE.md](./PACKAGE.md)                     | Packaging and release                                |
| [workflow/README.md](./workflow/README.md)     | Workflow spec (progressive disclosure & data deps)   |


Code entry points: `@dipper/agent` (`agent-loop`, `provider/`, `chat-turn`).

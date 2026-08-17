# Dipper AI Worker 通讯协议参考

本文档描述 Dipper Worker 中各程序角色之间的通讯协议，覆盖三类交互边界：**进程间**（渲染进程 ↔ Electron 主进程的 IPC、主进程 ↔ Agent Worker 的 UtilityProcess RPC）、**程序与模型**（Agent 与 LLM 提供商的 OpenAI 兼容 HTTP 协议、模型使用 skills 与工具的双向契约）、**程序与外部服务**（Agent 与 MCP Server 的 stdio / Streamable HTTP / SSE JSON-RPC）。每章包含消息格式、通道约定、调用语义与完整示例，供开发与排障参考。


## 1. 架构总览

应用由三层进程组成，协议在每层边界处不同：

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
           ├──▶ LLM Provider    HTTP（OpenAI 兼容）
           ├──▶ MCP Server      JSON-RPC 2.0（stdio / HTTP / SSE）
           └──▶ 子进程           exec / 脚本 / node / python
```

> ↓ / ↑ 表示消息方向；右侧 ◀── ──▶ 为通道；底部为 Agent 下辖的外部依赖。

| 边界 | 传输机制 | 消息格式 |
|------|----------|----------|
| Renderer → Main | Electron IPC (`ipcRenderer.invoke`) | 请求/响应，通道名 `agent:*`、`workspaces:*`、`browser:*` 等 |
| Main → Renderer | Electron IPC (`webContents.send`) | 单向推送事件，通道名 `agent:chat-event`、`agent:status-changed` 等 |
| Main → Agent Worker | `utilityProcess` + `parentPort` | JSON 消息：`call` / `call-res` / `event` / `host-req` / `host-res` |
| Agent → LLM | HTTP (OpenAI 兼容 / 自定义) | JSON, `messages` + `tools` |
| Agent → MCP Server | stdio / Streamable HTTP / SSE | JSON-RPC 2.0 |

## 2. Renderer ↔ Main：Electron IPC

### 2.1 请求 / 响应（invoke / handle）

Renderer 通过 `preload.ts` 暴露的 `window.dipper`（类型 `DipperWorkerAPI`，定义于 `worker/types.ts`）调用主进程。每个方法映射到一个 IPC 通道。

- **请求**：`ipcRenderer.invoke(channel, ...args)`
- **响应**：`ipcMain.handle(channel, handler)` 返回的 Promise 值
- 通道名以 `:` 分隔的命名空间前缀标识功能域：`agent:`、`workspaces:`、`browser:`、`terminal:`、`shell:`、`fs:`、`window:`、`screenshot:`、`bookmarks:`、`shortcuts:`、`prefs:`、`clipboard:`

**示例**：列出会话

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

### 2.2 单向推送（on / send）

主进程向渲染进程推送事件，渲染进程订阅：

- `ipcMain` 侧调用 `webContents.send(channel, payload)`
- `preload` 侧 `ipcRenderer.on(channel, cb)` 并返回取消订阅函数

**示例**：聊天流事件

```typescript
// worker/main.ts — 广播
function broadcastChatEvent(event: ChatStreamEvent): void {
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('agent:chat-event', event)
  }
}

// worker/preload.ts — 订阅（返回取消函数）
onChatEvent: (cb) => {
  const listener = (_event: Electron.IpcRendererEvent, ev: ChatStreamEvent) => cb(ev)
  ipcRenderer.on('agent:chat-event', listener)
  return () => ipcRenderer.removeListener('agent:chat-event', listener)
},
```

### 2.3 安全边界

- 渲染进程启用 `contextIsolation: true`、`nodeIntegration: false`、`sandbox: true`（`worker/main.ts`）。
- 只有 `preload.ts` 显式暴露的方法可达主进程。
- `agent:invoke` 通道（`worker/ipc/agent-ipc.ts`）只放行 `RENDERER_AGENT_INVOKE_METHODS` 白名单（`@dipper/agent` 的 `facade/renderer`），避免 XSS 重定向工作区或触发生命周期操作。

## 3. Main ↔ Agent Worker：UtilityProcess RPC

Agent 常驻于 Electron `utilityProcess`（脚本 `agent-host.js`），通过 `process.parentPort` 与主进程 `AgentBridge` 通讯。消息均为 JSON 对象，带 `type` 判别字段。消息类型与白名单在 `@dipper/agent`（`host-protocol` / `facade`）；桌面入口为 `worker/agent/agent-host.ts`。

### 3.1 消息类型

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

`ready` 携带协商结果：`capabilities`（如 `browser`、`secrets`）与当前激活的 `packs`（含工作区外部 pack）。
### 3.2 调用语义（request / response）

- 主进程发起 `{ type: 'call', id, method, args }`（见 `agent-bridge.ts` 的 `invokeOnce`）。
- Agent 执行后回 `{ type: 'call-res', id, ok, result | error }`。
- `id` 为 `c-<时间戳>-<自增序列>`，主进程 `pending` Map 按 id 匹配 Promise。
- 方法名必须是 `AgentRuntimeApi`（`@dipper/agent`）的成员；桌面 UtilityProcess 使用 `AGENT_INVOKE_METHODS`（Kernel ∪ Product），`child-host` 仅放行 `KERNEL_INVOKE_METHODS`。
- `AgentBridge.invoke` 是类型安全包装：方法名/参数元组/返回类型均由 `AgentRuntimeApi` 推导；若 worker 在调用间崩溃，自动重启并重试一次。

**示例**：主进程调用 `listSessions`

```typescript
// AgentBridge 侧
this.postToChild({ type: 'call', id: `c-${Date.now()}-${++this.seq}`, method: 'listSessions', args: [0, 30] })

// agent-host.js 侧收到
// → 校验 ALLOWED → dispatch('listSessions', [0, 30])
// → 回 { type: 'call-res', id, ok: true, result: { sessions: [...], hasMore: true } }
```

### 3.3 事件推送（单向）

Agent 主动推送 `{ type: 'event', event: 'chat' | 'status' | 'bot-status', ... }`，主进程 `onChildMessage` 分发给 `AgentBridgeEvents` 回调，最终由 `main.ts` 广播到渲染进程。

聊天流事件 `ChatStreamEvent`（`worker/types.ts`）是核心协议，完整列表：

| type | 方向 | 用途 |
|------|------|------|
| `status` | agent→renderer | 会话活动状态 `idle/thinking/responding/waiting/compacting/retry/error` |
| `text.delta` | agent→renderer | 文本增量（被 `StreamCoalescer` 合并，32ms / 96 字符） |
| `thinking.delta` | agent→renderer | 思考增量（同样合并） |
| `thinking.done` | agent→renderer | 思考块结束，带 `durationSec` |
| `progress` | agent→renderer | 工具实时进度（如下载 `detail`） |
| `tool.start` / `tool.end` | agent→renderer | 工具调用开始 / 结束，含 `toolCallId`、args、result |
| `permission.asked` | agent→renderer | 请求权限确认（`permissionId` + 分类） |
| `question.asked` | agent→renderer | 提问（`questionId` + options） |
| `subagent.start` / `subagent.end` | agent→renderer | 子代理生命周期 |
| `compaction.started` / `compaction.ended` | agent→renderer | 会话压缩 |
| `retry` | agent→renderer | 提供商重试信息 |
| `done` | agent→renderer | 一轮结束：`content` + `parts` + `durationSec` |
| `error` | agent→renderer | 错误，`error` 为 `'aborted'` 表示本地取消 |

**示例**：一次完整对话的事件序列（按 `requestId` 关联）

```jsonc
{ "requestId": "req-1", "type": "status", "activity": "thinking" }
{ "requestId": "req-1", "type": "thinking.delta", "delta": "用户想下载一个安装包，" }
{ "requestId": "req-1", "type": "tool.start", "tool": "download_url", "detail": "{\"url\":\"...\",\"path\":\"downloads/app.zip\"}", "toolCallId": "call_1" }
{ "requestId": "req-1", "type": "progress", "tool": "download_url", "detail": "正在下载 app.zip · 45% · 12.3 MB / 27.1 MB · 2.4 MB/s · 8 conn" }
{ "requestId": "req-1", "type": "tool.end", "tool": "download_url", "toolCallId": "call_1", "result": "Downloaded 27.1 MB\nmode: multi (8 connections)\npath: downloads/app.zip", "status": "done" }
{ "requestId": "req-1", "type": "text.delta", "delta": "已下载完成，文件在 " }
{ "requestId": "req-1", "type": "text.delta", "delta": "downloads/app.zip。" }
{ "requestId": "req-1", "type": "done", "content": "已下载完成，文件在 downloads/app.zip。", "parts": [...] }
{ "requestId": "req-1", "type": "status", "activity": "idle" }
```

### 3.4 反向调用（host-req / host-res）

Agent 需要调用宿主能力（浏览器、Provider 密钥）时，反向发送 `{ type: 'host-req', id, method, args }`。桌面侧经 `AgentBridge` 转到 **Cap 总线**，当前 wire **仅支持**：

- `cap.invoke` — 统一能力调用（`capabilityId` + `op` + 参数）；桌面实现为 `@dipper/host-desktop` 的 browser / secrets

Agent 侧经远程 CapRegistry / `parentInvoke`（`@dipper/agent` 的 `parent-rpc`），带超时。浏览器工具包通过 `browser-proxy` 走 `CAP_BROWSER`，不再使用独立的 `browserTool` / 明文密钥方法名。

**示例**：

```typescript
// Agent（worker 进程内）— 经 cap bus
await invokeCapability('secrets', /* op + args */)

// Wire 形态（示意）
// host-req: { method: 'cap.invoke', args: [capabilityId, ...] }
// → 主进程 CapRegistry → host-res
```

### 3.5 流合并（StreamCoalescer）

`@dipper/agent` 的 `stream-coalesce` 只合并 `text.delta` / `thinking.delta`（32ms 或 96 字符触发一次冲刷），其余事件类型（`progress`、`tool.start/end`、`status` 等）先冲刷待合并缓冲再透传，保证实时进度不被延迟。

## 4. Agent ↔ LLM：模型提供商协议

> 数据字段含义、发往/返回示例、本地落盘与**安全隐私**专述见 [MODEL-DATA.md](./MODEL-DATA.md)。本章侧重传输格式与调用语义。

Agent 通过 `buildLlmProvider(cfg)`（`@dipper/agent` provider）按配置组装主模型 + fallback 链，统一走 `llm.chat(messages, tools, opts)` 接口。传输为 HTTP JSON，OpenAI 兼容格式。核心类型定义于 `@dipper/agent` types 与 `@dipper/agent` provider/types。

### 4.1 统一接口

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
  onTextDelta?: (delta: string) => void      // 正文增量 → text.delta
  onThinkingDelta?: (delta: string) => void  // 思考增量 → thinking.delta
  model?: string                             // fallback 链覆盖模型
}
```

底层实现只有 `OpenAIProvider`（`worker/agent/provider/openai.ts`），兼容一切 OpenAI 兼容端点；`createProviderChain`（`worker/agent/provider/fallback.ts`）负责重试与多提供商降级。

### 4.2 消息格式（LlmMessage）

```typescript
// @dipper/agent types
export type ChatRole = 'system' | 'user' | 'assistant' | 'tool'

export type LlmMessage = {
  role: ChatRole
  content?: string
  /** OpenAI 兼容思考模型连续性字段（如 reasoning_content），非思考模型省略 */
  reasoning_content?: string
  tool_calls?: ToolCallDef[]      // assistant 主动发起工具调用
  tool_call_id?: string           // tool 回传时关联对应调用
  name?: string                   // tool 回传时携带工具名
}

export type ToolCallDef = {
  id: string
  type: 'function'
  function: { name: string; arguments: string }  // arguments 为 JSON 字符串
}
```

### 4.3 请求格式

`POST {apiBase}/chat/completions`，鉴权头 `Authorization: Bearer <apiKey>`（未配置 key 时省略，兼容本地服务），可附加 `extraHeaders`：

```jsonc
{
  "model": "gpt-4o",
  "messages": [
    { "role": "system", "content": "你是运行在本机的 AI 助手……" },
    { "role": "user", "content": "帮我下载 QQ 安装包" }
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

- 无 `onTextDelta` 回调时 `stream: false`（阻塞模式）；否则 `stream: true`。
- `tools` 为空数组时不发送 `tools` / `tool_choice` 字段。

### 4.4 响应格式（非流式）

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

客户端解析为 `LlmResponse`（`@dipper/agent` types）：

```typescript
export type LlmResponse = {
  content: string
  /** 推理内容：读 message.reasoning_content 或 reasoning 字段（思考模型） */
  reasoning?: string
  toolCalls: ToolCallRequest[]   // arguments 已 JSON.parse 为对象
  finishReason: string           // stop | tool_calls | length | ...
}
```

### 4.5 流式响应（SSE）

`stream: true` 时响应体为 SSE，按行分帧，每行 `data: <json>`，结束标记 `data: [DONE]`。增量字段在 `choices[0].delta`：

```jsonc
data: {"choices":[{"delta":{"reasoning_content":"用户要下QQ，先找官方链接…"}}]}

data: {"choices":[{"delta":{"content":"已下载完成，"}}]}

data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_abc123","function":{"name":"download_url","arguments":"{\"url\":"}}]}}]}

data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"https://...\"}"}}]}}]}

data: {"choices":[{"finish_reason":"tool_calls"}]}

data: [DONE]
```

处理规则（`OpenAIProvider.chatStream`）：

- `delta.content` → 追加正文并触发 `onTextDelta`
- `delta.reasoning_content` 或 `delta.reasoning` → 追加推理并触发 `onThinkingDelta`
- `delta.tool_calls` 按 `index` 归组累积，`name` 与 `arguments` 均按流式分片拼接
- 记录 `finish_reason`；流结束后把累积的 `tool_calls` 拼成完整 JSON 再 `JSON.parse`

### 4.6 工具调用多轮协议

Agent 与模型按「模型提议 → 程序执行 → 结果回传 → 再提议」循环（`agent-loop.ts` 主循环），每轮：

1. `llm.chat(messages, tools, opts)` 发起。
2. 若响应含 `toolCalls`：把 assistant 消息（含 `tool_calls`）追加进 `messages`，执行工具，再把每个结果作为 `role: 'tool'` 消息回传（`tool_call_id` 关联对应调用）。
3. 循环直至响应无 `toolCalls` 且产出 `content`。

**完整示例**（第二次请求的 body，携带第一轮的工具调用与结果）：

```jsonc
{
  "model": "gpt-4o",
  "messages": [
    { "role": "system", "content": "…" },
    { "role": "user", "content": "帮我下载 QQ 安装包" },
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

第三轮模型返回纯文本正文，`finishReason: 'stop'`，Agent 收到后完成回合。

边界情况（`agent-loop.ts` 内建协议）：

- **仅思考无正文**：模型用尽 `finishReason: 'length'` 或只产出了推理，Agent 追加一条系统 nudge（不重发 `reasoning_content`，避免撑爆上下文）再调一次无工具对话恢复正文。
- **工具轮次上限**：达到 `maxIterations`（默认 1000）后，追加一条"不要再调用工具"的用户消息，做一次无工具 wrap-up。
- **上下文预算**：`trimMessagesToTokenBudget` 发送前裁剪历史；`shrinkToolMessagesForBudget` 每轮后收缩旧的工具结果文本。

### 4.7 思考内容传递

- 请求侧：历史 assistant 消息若带 `reasoning_content` 则透传给模型（思考模型多轮连续性）；普通消息该字段被省略，避免严格 OpenAI 端点拒绝。
- 响应侧：非流式读 `message.reasoning_content` 或 `message.reasoning`；流式读 `delta.reasoning_content` 或 `delta.reasoning`。

### 4.8 重试与 fallback 链

`FallingBackProvider`（`worker/agent/provider/fallback.ts`）：

- 主模型 + 若干 fallback（`cfg.agents.modelSelection`），每步最多重试 2 次，退避 `800ms × 2^attempt`。
- 可重试判定 `isLlmRetryable`：连接类（connection refused / timeout / ECONNRESET / ENOTFOUND / fetch failed / network / EOF 等）与 HTTP `429 / 500 / 502 / 503 / 504`；`aborted` 与业务错误不重试。
- 触发重试/切换时调用 `onRetry` hook → 主循环转为 `ChatStreamEvent.retry` 事件（含 `attempt`、`message`、`nextMs`、`provider`）推送 UI，并置 `status: retry`。

### 4.9 模型列表

`GET {apiBase}/models`（带同一鉴权头），响应 `{ "data": [{ "id": "gpt-4o" }, ...] }`，客户端排序后返回。对应渲染进程的 `listModels` IPC。

### 4.10 系统提示组装

每次对话的系统提示由多个模块拼接（`agent-loop.ts`），顺序即注入优先级：

```
DEFAULT_SYSTEM（内置人格与行为准则）
  + systemExtra（subagent 等场景附加）
  + parallelHint（并行子代理能力提示）
  + learning（记忆注入：用户偏好 / 项目笔记）
  + skills（技能索引：name + description，按需 read_file 正文）
  + workflows（工作流索引）
  + safetyBlock（安全合规约束）
  + mathRules（数学规则）
  + osRules（操作系统规则）
  + langRules（语言指令）
```

上下文历史经 `buildContextualHistory`（`worker/agent/context.ts`）按三层选取后同样拼入，最后整体经 `trimMessagesToTokenBudget` 裁剪到 token 预算：

| 层 | 来源 | 内容 | 配置项 |
|----|------|------|--------|
| ① 摘要 | `session.summary`（压缩产出） | 最近成功任务的滚动摘要，合并进唯一的 system 消息（严格 chat 模板只允许一条 system） | — |
| ② 原文 | 会话尾部 | 最近 `recentTurnsKept` 个完整轮次逐字保留（按 user 消息计数，含其后全部回复） | `agents.recentTurnsKept`（默认 `2`；`0` = 关闭） |
| ③ 检索 | 全部历史（尾部 80 条） | 本地 embedding 相似度检索，排除②已覆盖的消息 | `agents.embeddingTopK`（默认 `6`；`0` = 关闭） |

- 三层按时间正序合并输出；②的 id 集合同时是③的排除集，保证同一消息只发送一次。
- 超预算裁剪优先级（`tokens.ts` 从最旧非 system 消息开始丢）：当前问题 > 摘要 > ②原文 > ③检索到的旧消息。
- `recentTurnsKept` / `embeddingTopK` 定义于 `WorkspaceConfig['agents']`（`@dipper/agent` types），写入 `worker.json`；越界值（非整数 / 负数 / >20）归一化回退默认值（`@dipper/agent` config）。

### 4.11 会话压缩与最近任务摘要

会话历史永不修剪（UI 保留全部消息），仅靠"摘要 + 原文 + 检索"控制发往模型的 token。压缩逻辑位于 `worker/agent/compaction.ts`：

- **触发**：距上次压缩新增消息 ≥28 条或新增 tokens ≥12k（`shouldCompact`）。`session.compactedMessageCount` 记录上次压缩时的消息数作为增量水位，避免每轮重复触发。设置页"压缩会话"手动触发同一逻辑（`runtime.ts`）。
- **成功任务选区**：`recentSuccessfulTaskMessages` 从尾部倒序收集最近 7 条"成功任务"——assistant 消息中所有 tool / subagent part 的 `status` 均为 `done`（任一 `error` 即整轮不计入；纯文本回复无任务 parts 也不计入），并配对其前最近的 user 诉求。
- **生成**：7 条任务格式化后（≤32k 字符）由 LLM 产出 ≤400 词的纯文本摘要，存储为 `session.summary`，前缀 `[Recent task summary]`。与旧版"全对话结构化 JSON 主题"不同，新摘要只覆盖最近任务滚动窗口，不做增量合并，早期任务自然滚出。
- **消费**：`buildContextualHistory` 剥除 `[Conversation summary]` / `[Recent task summary]` 前缀后，将摘要正文以 `[Recent task summary]` 前缀并入唯一的 system 消息。
- **旧数据兼容**：旧版 `[Conversation summary]` JSON 摘要同样被剥除前缀后进入 system，首次压缩即覆盖为新格式。

## 5. 模型 ↔ 程序：Skills 与工具交互协议

本节描述模型（LLM）如何通过系统提示中的技能索引发现 skills，以及如何通过工具调用让程序执行实际操作。这是程序给模型提供能力的双向契约。

### 5.1 Skills 的三层渐进式加载

技能采用"索引 → 正文 → 参考资料"三层结构，平衡上下文占用与信息完备度（`worker/agent/skills.ts`）：

| 层 | 内容 | 何时加载 | 代码 |
|----|------|----------|------|
| 第一层 · 索引 | 每个 skill 的 `name` + 相对路径 + 简述 + `[+references]` 标记 | 每次对话注入系统提示（token 预算约 700） | `loadSkillsPrompt` |
| 第二层 · 正文 | `skills/<name>/SKILL.md` 完整内容 | 模型用 `read_file` 按需读取 | `read_file` 工具 |
| 第三层 · 参考资料 | `skills/<name>/references/` 下的大文件 | 模型发现正文里指引时再读 | `read_file` 工具 |

索引生成规则（`listSkills`）：

- 工作区 `skills/` 优先，同名时内置 skills 不重复列出；启动时 `seedBuiltinSkills` 把内置技能播种到工作区。
- 每个 skill 的摘要取自 `SKILL.md` frontmatter 的 `description`（截断 120 字符），无 frontmatter 时回退正文首行。
- 按与用户提问的匹配度排序：命中名称 +5、命中名称片段 +2、命中摘要 token +1；顶部 4 个高匹配项带完整摘要，其余仅列路径。
- 目录名 / frontmatter `name` 不符或 schema 校验失败会在启动日志告警（`skill-schema.ts`）。

**SKILL.md 规范**（`skill-schema.ts` 强制校验，允许键：`name`、`description`、`license`、`homepage`、`version`、`always`、`metadata`）：

```markdown
---
name: download
description: "Use for any network file download task — the default download path: installers, archives, large binaries, torrent/magnet/metalink. Triggers: download, 下载, fetch file, get installer, torrent, magnet, .torrent, metalink."
---

# Download — 正文写：When to use / How to call / Conventions / Troubleshooting
```

**注入系统提示后的效果**（模型看到的技能索引）：

```
Available skills (read SKILL.md with read_file before using one; skills with references/ have extra files you may read on demand):
Likely relevant:
- download: skills/download/SKILL.md — Use for any network file download task — the default download path… [+references]
All skills:
- cron: skills/cron/SKILL.md
- …and 12 more in workspace/skills
```

### 5.2 模型的技能使用流程

模型遵循"发现 → 读取 → 执行"三步，程序侧全程通过通用工具协议支撑：

1. **发现**：系统提示的技能索引列出候选，按匹配度排序。
2. **读取**：模型判断需要时，调用 `read_file` 读取 `skills/<name>/SKILL.md`；正文提示 `references/` 时再按需读取参考资料。
3. **执行**：SKILL.md 正文里的指令最终都落到内置工具调用（如 `download_url`、`exec`、`web_fetch`）。

```jsonc
// 模型：读取 download 技能正文
{
  "tool_calls": [{
    "id": "call_read1",
    "function": {
      "name": "read_file",
      "arguments": "{\"path\": \"skills/download/SKILL.md\"}"
    }
  }]
}

// 程序执行后回传结果
{ "role": "tool", "tool_call_id": "call_read1", "name": "read_file",
  "content": "# Download — built-in naria2 engine…\n## When to use\nUse **`download_url`** for every network file download…" }
```

### 5.3 工具声明协议

程序侧工具必须满足 `Tool` 契约（`@dipper/agent` 的 `types`）才能注册进 `ToolRegistry`：

```typescript
export type Tool = {
  name: string                       // 协议标识，如 download_url / read_file
  description: string                // 给模型的自然语言说明（何时用、干什么）
  parameters: Record<string, unknown> // JSON Schema（type/properties/required）
  meta?: ToolMeta                    // parallelSafe / permission（权限门）
  execute: (params, ctx) => Promise<string>  // 程序执行体
}
```

注册后 `listDefs()` 生成 OpenAI 兼容 `ToolDef[]` 注入每次请求的 `tools` 字段。子代理场景用 `cloneWithout(exclude)` 屏蔽部分工具。

**工具包（tool packs）**（`createBuiltinRegistry`，经 PluginRegistry 贡献）：

| Pack | 工具示例 | 说明 |
|------|----------|------|
| `core` | `read_file`、`write_file`、`exec`、`web_fetch`、`ask_user`、`task`、workflow_* | 文件系统 / 搜索 / 执行 / 网络 / 交互 / 工作流 |
| `media` | `download_url`、`archive`、`ffmpeg` | 下载与媒体 |
| `browser` | `browser_*`（需 `CAP_BROWSER`） | 代理到主进程 WebContentsView + CDP |
| `content` | `install_skill`、`install_workflow` | 内容安装辅助 |
| 工作区外部 | 如 `example_echo` | `<workspace>/plugins/*/manifest.json` — 见 [PLUGINS.md](./PLUGINS.md) |
| MCP | `mcp__<server>__<tool>` | 动态挂载外部 MCP 工具 |

**超大文件读写**（分页读 + 分块写；禁止一次整文件传输）：

| 工具 | 上限 | 用法 |
|------|------|------|
| `read_file` 无 `offset`/`limit` | 约 2MB 硬拒绝；否则约 8KB 头部 + 续读提示 | 优先 `offset` + `limit`（如 200 行），跟随 `next: offset=…` |
| `write_file` / `append_file` 的 `content` | 每次约 6KB | 先 `write_file` 骨架，再多次 `append_file` |
| `edit_file` | 字符串替换约 8MB；按行模式可流式 | `old_text` 或 `start_line`/`end_line`；超大字符串改用按行或 `exec` |

### 5.4 工具调用完整生命周期

一次工具调用从模型发起到最后回传，贯穿 §4.6 的多轮协议，并叠加权限门、进度推送、并行调度：

```
模型发起 tool_calls
  │
  ├─ ① 权限门（agent-loop.ts）
  │    classifyToolPermission → 需要确认?
  │    └─ permission.asked 事件 ─→ UI 弹窗 
  │         ← replyPermission(permissionId,
  │             once|always|reject)
  │    reject → 抛错终止本轮
  │
  ├─ ② 进度与开始（emit）
  │    tool.start 事件（tool + args 摘要）
  │    progress 事件（实时进度 detail）
  │
  ├─ ③ 执行（registry.execute）
  │    execute(params, ctx)
  │    ctx.signal → 中止
  │    ctx.onProgress(tool, detail) → progress
  │    ctx.askPermission / ctx.askUser → 询问
  │
  ├─ ④ 完成/失败（emit）
  │    tool.end 事件（result/status/truncated）
  │    结果截断：part.result ≤4000 字符，
  │              tool.end result ≤2000 字符
  │
  └─ ⑤ 回传模型（messages.push）
       { role: 'tool', tool_call_id, name,
         content: result }
```

**权限门**（`ToolPermissionMeta`，`@dipper/agent` types）：

- 无 `meta.permission` 的工具自动放行。
- `classify(args, ctx)` 返回 `null` 自动放行；返回 `{ kind, title, detail }` 则需用户确认（`alwaysConfirm: true` 时即使在会话级"始终允许"下也强制询问）。
- 典型策略：`read_file` 只读且 `parallelSafe: true`；`edit_file` 工作区内自动放行、工作区外询问；`download_url` 对 magnet/torrent 分类为 P2P 下载强制确认。

**并行调度**：

- `parallelSafe` 标记的工具可并行执行（`Promise.allSettled`），如 `read_file`、`web_fetch`。
- 非并行工具串行执行；`task` 子代理按 CPU 核数池化（`mapPool`）。
- 同一调用指纹重复超过阈值触发"死循环"确认（`doom_loop` 权限）。

### 5.5 端到端示例：模型用 skill + 工具完成下载

以"帮我下载 QQ 安装包"为例，展示模型、程序、UI 的完整交互序列：

```jsonc
// ① 程序组装系统提示（含技能索引），调 LLM
POST /chat/completions
{
  "model": "gpt-4o",
  "messages": [
    { "role": "system", "content": "…Available skills:\n- download: skills/download/SKILL.md — …\n- …" },
    { "role": "user", "content": "帮我下载 QQ 安装包" }
  ],
  "tools": [ { "type": "function", "function": { "name": "download_url", … } },
              { "type": "function", "function": { "name": "read_file", … } } ],
  "tool_choice": "auto"
}

// ② 模型读到 download 技能索引，先用 read_file 读正文
→ 程序执行 read_file，回传 skill 正文
→ 模型在正文指引下调用 download_url
{ "tool_calls": [{
    "id": "call_dl1",
    "function": { "name": "download_url",
      "arguments": "{\"url\":\"https://dldir1.qq.com/qqfile/QQ.exe\",\"path\":\"downloads/QQ.exe\",\"connections\":8}" }
}]}

// ③ 程序执行：权限门分类（http 下载 → 自动放行）
//    emit tool.start + progress
{ "requestId": "req-1", "type": "tool.start", "tool": "download_url",
  "detail": "{\"url\":\"https://…\",\"path\":\"downloads/QQ.exe\",\"connections\":8}", "toolCallId": "call_dl1" }
{ "requestId": "req-1", "type": "progress", "tool": "download_url",
  "detail": "正在下载 QQ.exe · 45% · 134.5 MB / 299.3 MB · 2.4 MB/s · 8 conn" }
//  …UI 实时渲染进度条 …

// ④ 下载完成，emit tool.end
{ "requestId": "req-1", "type": "tool.end", "tool": "download_url", "toolCallId": "call_dl1",
  "result": "Downloaded 299.3 MB\nmode: multi (8 connections)\npath: downloads/QQ.exe",
  "status": "done" }

// ⑤ 结果回传模型，模型产出最终回复
{ "role": "assistant", "content": "", "tool_calls": [{ "id": "call_dl1", … }] }
{ "role": "tool", "tool_call_id": "call_dl1", "name": "download_url",
  "content": "Downloaded 299.3 MB\nmode: multi (8 connections)\npath: downloads/QQ.exe" }

→ 第三轮：模型返回正文 "QQ 安装包已下载到 downloads/QQ.exe（299.3 MB）。"
→ 程序 emit done 并持久化消息，UI 渲染完整回复
```

### 5.6 工具协议要点总结

| 约定 | 说明 |
|------|------|
| 工具名即协议标识 | `download_url`、`read_file`、`mcp__<server>__<tool>`，同名工具后注册覆盖 |
| 描述即语义 | 模型的选工具依据是 `description`，必须写明触发条件与默认路径 |
| JSON Schema 参数 | `arguments` 必须是合法 JSON 字符串，程序端解析失败容错为空对象 |
| 结果回传格式 | 纯文本多行，`tool_call_id` 一一对应；超长截断（4000/2000 字符）|
| 权限门 | 写操作/越界操作经 `permission.asked` 让用户确认，决策 `once/always/reject` |
| 进度 | `onProgress` → `progress` 事件流式推送 UI，不阻塞模型轮次 |
| 中止 | 用户点击中止 → `stopChat` → AbortSignal → 工具抛 `aborted` |
| 并行 | `parallelSafe: true` 工具同轮并发；`task` 子代理按核数池化 |

## 6. Agent ↔ MCP Server：JSON-RPC

`McpManager`（`worker/agent/mcp.ts`）实现 MCP 客户端，支持三种传输，协议为 JSON-RPC 2.0。

### 6.1 传输抽象

`McpTransport` 接口（`worker/agent/mcp/types.ts`）：

```typescript
interface McpTransport {
  request(method: string, params: unknown, signal?: AbortSignal): Promise<unknown>
  notify(method: string, params: unknown): void
  close(): void
}
```

### 6.2 stdio（`mcp/stdio.ts`）

- 通过 `spawn` 启动子进程，stdin/stdout 传输。
- 帧格式：优先 `Content-Length` 头（MCP 标准），无头时回退 NDJSON 单行。
- Windows 下 `npx` / `npm` 自动解析为 `.cmd`。

```jsonc
// → stdout（请求）
{ "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {} }
// ← stdin（响应）
{ "jsonrpc": "2.0", "id": 1, "result": { "tools": [...] } }
```

### 6.3 Streamable HTTP（`mcp/http.ts`）

- 单端点 POST，`Accept: application/json, text/event-stream`。
- 响应可以是普通 JSON 或 SSE 流；服务器返回 `Mcp-Session-Id` 头则后续请求回传。
- 超时默认 30s。

### 6.4 调用流程

1. `prepare(workspace, servers)` 缓存配置，跳过禁用 / 缺命令 / 缺 URL 的服务器（含 `chrome-devtools` 等内置忽略项）。
2. 懒连接：`ensureRuntimeMcpTools` 在首次聊天时触发 `connectMcpServers`，`tools/list` 拉取工具列表。
3. Agent 通过工具注册表调用 `mcp__<server>__<tool>`，底层执行 `tools/call`。
4. 配置变更时 `rebuildRuntimeTools` 重建内置工具并刷新 MCP 工具，配置未变时保持已有连接避免重连风暴。

## 7. 相关文件索引

| 文件 | 内容 |
|------|------|
| `packages/protocol` | Capability / pack / 插件契约 |
| `packages/kernel` | Cap 总线、传输、PluginRegistry、磁盘加载 |
| `packages/agent` | LocalAgentRuntime、tools、facade、host-protocol、runners |
| `packages/host-desktop` / `host-cli` | 宿主能力实现 |
| `worker/types.ts` | 桌面 IPC 类型；部分状态类型再导出自 `@dipper/agent` |
| `shared/types.ts` | renderer 统一导入点 |
| `worker/agent/agent-bridge.ts` | 主进程桥接（call / cap.invoke / 流合并） |
| `worker/agent/agent-host.ts` | UtilityProcess 入口 |
| `worker/agent/child-host.ts` | child_process 入口（Kernel 白名单） |
| `worker/hosts/cli/` | embedded / child 库宿主 |
| `worker/ipc/agent-ipc.ts` | renderer↔main agent IPC（Renderer facade） |
| `worker/preload.ts` | contextBridge 暴露 `window.dipper` |
| `worker/main.ts` | IPC 注册、事件广播、AgentBridge 生命周期 |
| `skills/<name>/SKILL.md` | 技能定义 |
| `examples/plugins/` | 工作区工具包示例 |

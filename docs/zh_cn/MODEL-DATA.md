# 程序与模型交互数据说明

本文说明 Dipper Worker **本机程序**与 **LLM 提供商**之间交换的数据：有哪些字段、从哪里来、发往哪里、如何本地保存，以及安全与隐私边界。协议细节（HTTP 路径、SSE 分帧、IPC 通道）见 [PROTOCOL.md](./PROTOCOL.md) 第 4 章。

---

## 1. 数据流总览

```text
用户输入 / 附件 / 会话历史（本地）
        │
        ▼
┌───────────────────┐
│  Agent 组装上下文  │  system + 摘要 + 历史 + 工具定义
└─────────┬─────────┘
          │  HTTPS（OpenAI 兼容）
          │  Authorization: Bearer <apiKey>
          ▼
┌───────────────────┐
│  LLM 提供商端点    │  用户自配 apiBase（无 Dipper 中间服务）
└─────────┬─────────┘
          │  文本 / 思考 / tool_calls
          ▼
┌───────────────────┐
│  本机执行工具       │  结果再回传模型（多轮）→ 最终回复写入会话
└───────────────────┘
```

要点：

- **无云端中继**：对话请求由本机直接发往你配置的 `apiBase`，Dipper 不托管用户对话内容。
- **密钥与正文分离**：API Key 经 OS `safeStorage` 加密存于 `~/.dipper-worker/secrets.json`；会话正文在工作区本地库，不随配置面板明文下发。
- **发往模型的内容可控**：通过「摘要 + 近轮原文 + 检索」与 token 预算裁剪，避免把整段历史无节制上传。

---

## 2. 发往模型的数据（Request）

### 2.1 载荷结构


| 字段            | 类型             | 说明                                  |
| ------------- | -------------- | ----------------------------------- |
| `model`       | string         | 当前主模型或本轮覆盖模型                        |
| `messages`    | `LlmMessage[]` | 系统提示 + 上下文历史 + 本轮用户消息 +（多轮时）工具调用与结果 |
| `tools`       | 工具定义数组         | 本轮可用 function schema；空则不发送          |
| `tool_choice` | `"auto"`       | 有 tools 时固定                         |
| `max_tokens`  | number         | 来自 Agent 配置                         |
| `temperature` | number         | 来自 Agent 配置                         |
| `stream`      | boolean        | UI 流式时为 `true`                      |


鉴权：`Authorization: Bearer <apiKey>`（未配置 key 时省略，便于本地模型）。部分厂商用自定义头（见各 vendor 适配）。

### 2.2 `messages` 角色与含义


| `role`      | 内容来源                                         | 是否可能含用户隐私             |
| ----------- | -------------------------------------------- | --------------------- |
| `system`    | 内置人格、技能/工作流**索引**、记忆摘要、安全与语言规则、近期任务摘要        | 中：记忆与摘要可能含用户偏好/项目事实   |
| `user`      | 用户输入、附件路径说明、历史用户轮                            | **高**：用户原文与附件引用       |
| `assistant` | 历史回复；含 `tool_calls` / 可选 `reasoning_content` | 中：回复与工具参数可能回指本地路径     |
| `tool`      | 本机工具执行结果（`tool_call_id` 关联）                  | **高**：文件片段、命令输出、网页正文等 |


类型定义见 `@dipper/agent`（`LlmMessage` / `ToolCallDef`）。

### 2.3 系统提示由哪些模块拼成

顺序即注入优先级（`agent-loop.ts`）：

1. 默认人格与行为准则（`DEFAULT_SYSTEM`）
2. 场景附加（如子代理）
3. 并行子代理能力提示
4. **学习记忆**（用户偏好 / 项目笔记摘要）
5. **技能索引**（name + description；正文按需 `read_file`）
6. **工作流索引**
7. 安全合规块（若开启）
8. 数学 / OS / **界面语言**指令

### 2.4 历史如何进入模型（不会整库上传）

UI 可保留完整会话；**发往模型**的历史由三层组装（`buildContextualHistory`）：


| 层      | 内容                                          | 配置                            |
| ------ | ------------------------------------------- | ----------------------------- |
| ① 摘要   | 会话压缩产出的「近期成功任务」摘要，并入 system                 | 自动 / 手动压缩                     |
| ② 近轮原文 | 最近 `recentTurnsKept` 个完整轮次（默认 2）            | `agents.recentTurnsKept`      |
| ③ 检索   | 本地 embedding 相关旧消息，最多 `embeddingTopK`（默认 6） | `agents.embeddingTopK`；`0` 关闭 |


发送前再经 `trimMessagesToTokenBudget` / `shrinkToolMessagesForBudget` 裁剪，优先保住当前问题与摘要。

### 2.5 不会发往模型的数据（本机留存）


| 数据                | 存放                              | 说明                                                      |
| ----------------- | ------------------------------- | ------------------------------------------------------- |
| API Key 明文        | OS 加密的 `secrets.json`           | 仅请求鉴权头使用；`getConfig` 返回脱敏（`hasApiKey` / `apiKeyLength`） |
| 完整会话 SQLite / 消息行 | 工作区 `sessions/`                 | 含未入选上下文的旧消息                                             |
| 学习日志              | `.dipper-worker/learning.jsonl` | 后台沉淀，默认不注入 UI                                           |
| 浏览器 Cookie / 缓存   | Electron session                | 不随 chat completions 上传                                  |
| 工具大结果溢出文件         | `outputs/tool-results/`         | 仅摘要或截断文本进上下文                                            |


---

## 3. 模型返回的数据（Response）

### 3.1 逻辑结果（`LlmResponse`）


| 字段             | 说明                                 |
| -------------- | ---------------------------------- |
| `content`      | 对用户可见的正文                           |
| `reasoning`    | 思考模型推理文本（映射 UI `thinking`）         |
| `toolCalls`    | 解析后的工具名 + 参数对象                     |
| `finishReason` | `stop` / `tool_calls` / `length` 等 |


流式时以 SSE `delta.content` / `delta.reasoning_content` / `delta.tool_calls` 增量到达，再在本机归组。

### 3.2 多轮工具循环时的数据往返

```text
模型 → tool_calls（意图）
程序 → 执行工具（权限门控后）
程序 → role:tool 结果写回 messages
模型 → 再提议或最终 content
```

工具结果会进入**后续请求**的上下文，因此本地文件片段、命令输出等可能再次出现在发往提供商的 JSON 中——这是 Agent 能力的必要代价，见第 6 章隐私提示。

---

## 4. 本地持久化（与模型交换后的落盘）


| 位置                                     | 内容                                                                          |
| -------------------------------------- | --------------------------------------------------------------------------- |
| 会话库 `messages`                         | `id` / `role` / `content` / `parts` / `timestamp` / `durationSec` / `usage` |
| `session.summary`                      | 压缩摘要（不单独占一条 UI 消息）                                                          |
| `memory/`、`skills/`                    | 回合结束后台学习（可关闭或受置信度过滤）                                                        |
| `uploads/` / `downloads/` / `outputs/` | 附件、下载、产物                                                                    |


消息行上的 `timestamp` 用于 UI 时间分隔；`usage` 为提供商回报或估算的 token 用量。

---

## 5. 示例

### 5.1 首轮请求（无工具调用）

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
      "content": "You are AI Worker …\n\n[Skills]\n- make-pdf: …\n\nCRITICAL language rules … 简体中文 …"
    },
    {
      "role": "user",
      "content": "把 outputs/notes.md 总结成三句话"
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

### 5.2 第二轮：带回工具结果

模型先返回 `tool_calls`；本机执行 `read_file` 后再次请求：

```json
{
  "model": "deepseek-chat",
  "messages": [
    { "role": "system", "content": "…" },
    { "role": "user", "content": "把 outputs/notes.md 总结成三句话" },
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
      "content": "# Notes\n- 里程碑 A 已完成\n- 下周发布 beta\n…"
    }
  ],
  "tools": [ /* 同上一轮 */ ],
  "tool_choice": "auto",
  "stream": true
}
```

第三轮模型返回纯文本 `content`，`finish_reason: "stop"`，写入会话并展示给用户。

### 5.3 流式增量（示意）

```text
data: {"choices":[{"delta":{"reasoning_content":"先读文件再概括…"}}]}

data: {"choices":[{"delta":{"content":"1. "}}]}

data: {"choices":[{"delta":{"content":"里程碑 A 已完成。"}}]}

data: {"choices":[{"finish_reason":"stop"}]}

data: [DONE]
```

### 5.4 配置脱敏（UI 可见，非发往模型）

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

明文 Key 仅经 `reveal-api-key` 专用通道、用户确认后短暂展示。

---

## 6. 数据安全与隐私

### 6.1 信任边界


| 边界           | 措施                                                            |
| ------------ | ------------------------------------------------------------- |
| 渲染进程 ↔ 主进程   | `contextIsolation`、无 Node 集成、preload 白名单、`agent:invoke` 方法白名单 |
| 主进程 ↔ Agent  | UtilityProcess RPC，方法受 `AgentRuntimeApi` / facade（`@dipper/agent`）约束 |
| Agent ↔ 模型   | 仅到用户配置的 `apiBase`；Key 不进工作区、不进学习产物                            |
| Agent ↔ 公网工具 | URL 经 `net-guard` 拒绝私网 / 元数据地址等（降低 SSRF）                      |
| 文件与命令        | 工作区路径守卫、授权文件夹、PermissionGate 交互确认危险操作                         |


### 6.2 密钥与敏感配置

- API Key：**不写** `worker.json` 明文；迁移后存 `~/.dipper-worker/secrets.json`（优先 `safeStorage` 加密）。
- `getConfig` / 设置页使用 `redactConfig`，不回传明文 Key。
- 工作区内会话、记忆、技能目录**不存放**提供商密钥。

### 6.3 对话与文件隐私（重要）

1. **提供商可见范围**
  发往模型的 JSON 中可能包含：用户输入、近轮历史、检索到的旧消息、工具读到的文件片段、命令输出、网页抓取结果、记忆摘要。  
   **这些内容的隐私策略由你所选的模型提供商决定**（日志、训练、留存期限等）。请阅读对应服务商条款；对高度敏感数据应使用本地/私有端点，或避免让 Agent 读取相关文件。
2. **本机默认**
  Dipper 不以中间服务器形式收集对话。卸载或删除工作区 / `~/.dipper-worker` 即清除本机侧对应数据（需自行备份）。
3. **工具扩大暴露面**
  一旦模型调用 `read_file` / `exec` / `web_fetch` 等，结果会进入后续模型请求。权限提示与「限制在工作区」可降低误伤，但不能阻止你已授权操作把内容送入模型上下文。
4. **MCP / 第三方技能**
  外部 MCP 与安装的技能可能访问网络或本地资源；仅安装可信来源，并关注其权限提示。
5. **学习与记忆**
  回合结束后台可能写入 `memory/` 与技能草稿。低置信度结果会丢弃；仍建议定期审阅 `memory/USER.md` 与笔记，删除不希望长期保留的条目。
6. **传输**
  使用 `https://` 的 `apiBase`；自签或明文 HTTP 仅建议在可信局域网本地模型场景。

### 6.4 用户可采取的实践

- 敏感仓库：关闭或不使用会读取全盘的授权目录；高危命令一律拒绝。
- 合规场景：选用支持零留存 / 企业合同的端点，或完全离线模型。
- 减少上传面：调低 `recentTurnsKept` / `embeddingTopK`，定期压缩会话，避免在对话中粘贴密钥。
- 清理：使用设置中的浏览数据清理、工作区清理工具；删除不需要的 `uploads/` / `outputs/`。

### 6.5 安全相关代码索引


| 模块                                        | 作用              |
| ----------------------------------------- | --------------- |
| `worker/secrets-store.ts`                 | API Key 加解密读写   |
| `@dipper/agent` `config` → `redactConfig` | 配置脱敏            |
| `@dipper/agent` `net-guard`               | 公网 URL / 私网拦截   |
| `@dipper/agent` `permissions`             | 工具权限门控          |
| `@dipper/agent` `context`                 | 发往模型的历史选择       |
| `@dipper/agent` `provider/openai`         | HTTP 请求与 SSE 解析 |


---

## 7. 相关文档


| 文档                                         | 内容                                     |
| ------------------------------------------ | -------------------------------------- |
| [PROTOCOL.md](./PROTOCOL.md)               | IPC、RPC、OpenAI 兼容协议、Skills/MCP 契约与完整报文 |
| [PACKAGE.md](./PACKAGE.md)                 | 打包与发行                                  |
| [workflow/README.md](./workflow/README.md) | 工作流规范（渐进式披露与数据依赖）                      |


代码入口：`@dipper/agent`（`agent-loop`、`provider/`、`chat-turn`）。
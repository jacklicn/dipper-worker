#  Dipper Worker

> 桌面级 AI Worker · 人工智能协作助手
>
> 简单、效率、可靠、经济。

Dipper Worker 是一款运行在桌面端的 AI 协作助手。通过对话即可完成文件操作、代码执行、网页检索、浏览器自动化、图片文字识别、文档生成等工作，并提供内置浏览器、终端、截图、收藏夹等桌面协作能力。

English: [README.md](./README.md).

## 特性

- **简单**：添加工作区 → 填入 API Base / Key / Model → 即可对话。内置 20 家主流模型服务商目录（DeepSeek、智谱、通义千问、豆包、Kimi、Google、OpenAI、Anthropic、xAI 等），一键选择并自动拉取模型列表。
- **效率**：Agent Worker 调度内置工具包（外加可选工作区插件与 MCP）；回合结束后台沉淀记忆与可复用技能，越用越顺手；explore 子代理按 CPU 核数并行。
- **可靠**：密钥经 OS 安全存储（safeStorage）加密保存；权限门控 + 授权文件夹 + 路径守卫 + 网络守卫（SSRF 防护）多重约束；会话本地持久化。
- **经济**：纯本地桌面应用，无订阅、无中间服务；自带国内镜像打包，开箱即用。对话自动节约词元使用量，发送前按上下文预算裁剪最旧消息、长会话自动摘要压缩，避免超长上下文拉高每次请求费用。

## 桌面协作能力

- **内置浏览器**：多标签页、前进/后退/刷新、收藏夹（书签库 + 悬浮覆盖层）、浏览数据清理、浏览器指纹隔离、打开本地 HTML / 图片。
- **内置终端**：默认工作目录为当前工作区，可新建 / 重启 / 结束会话。
- **文件面板**：浏览工作区目录，快速打开 / 在文件夹中显示 / 下载文件。
- **截图**：全局快捷键唤起截图，支持标注（矩形 / 箭头 / 文字 / 画笔）、颜色拾取。
- **系统托盘**：关闭窗口驻留托盘，可随时唤回；支持单实例锁。
- **会话管理**：分组、拖拽、置顶、归档、搜索、重命名、上下文压缩。
- **设置**：AI 服务商、Agent 参数、权限与授权文件夹、快捷键、外观（主题 / 布局 / 字体缩放）。
- **中英文双语**：界面语言自动检测，可随时切换。

## 自我学习

每个回合结束后台静默沉淀：

- 用户偏好与习惯 → `memory/USER.md`
- 项目事实 / 决策 → 可检索的记忆笔记
- 可复用的经验 → `skills/*/SKILL.md`（下次自动被 agent 加载）
- 可复用的流程 → `workflows/*/WORKFLOW.md`（mermaid 编排 + 步骤 + 规则，agent 按流程执行）

低置信度结果自动丢弃，日志记录在 `.dipper-worker/learning.jsonl`，默认不打扰。

## 工作区

- **单工作区**：侧栏 `+` 添加或更换目录；可重命名、更换颜色 / 图标、打开文件夹、移除（仅清除注册，不删磁盘）。
- **全局配置（含敏感信息）**：`~/.dipper-worker/worker.json` —— Provider / API Key / Model / MCP / Agent 参数、工作区注册。
  - 可选 `retention` 块控制数据清理参数（缺省用内置默认值）：`maxUserMemoryBullets`、`maxMemoryNotes`、`toolResultRetentionMs`、`learningLogRetentionMs` / `learningLogPruneMinSize` / `learningLogPruneIntervalMs`。
- **工作区内（无密钥）**：`sessions/`、`memory/`、`skills/`、`workflows/`、`uploads/`、`downloads/`、`outputs/`、`plugins/`；分组 / 权限 / 授权目录 / 外观档案在 `<workspace>/.dipper-worker/`。
- **工作区插件**：安装到 `<workspace>/plugins/<pack>/`（`manifest.json` + 入口）。所有外部 pack 共用一个插件宿主子进程，且属**同一工作区信任域**（pack 之间不互相隔离）。启动工作区时加载；文件变更后**热重载**（空闲时，按变更种类选择性处理）。可用 `reloadWorkspace()` 强制全量刷新。视为可信本地代码；不可覆盖内置 packId / 工具名。示例：`examples/plugins/echo-pack/`。
- **安全**：API Key 仅存于系统安全存储（`secrets.json`，safeStorage 加密）；`getConfig` 返回前脱敏，明文密钥仅经 `reveal-api-key` 专用通道并在应用内确认后展示。

## 架构

微内核式分包：共用 `@dipper/*`；Electron 只是其中一种产品宿主。

```text
┌─ 桌面产品 ───────────────────────────────────────────────────┐
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

┌─ 库宿主 · worker/hosts/cli ──────────────────────────────────┐
│  embedded (in-process)  │  child_process → child-host        │
│  @dipper/host-cli       │  KERNEL_INVOKE_METHODS only        │
└──────────────────────────────────────────────────────────────┘
```


| 包                      | 职责                                                         |
| ---------------------- | ---------------------------------------------------------- |
| `@dipper/protocol`     | Capability / pack ID、ops、插件契约                              |
| `@dipper/kernel`       | CapRegistry、传输、PluginRegistry、磁盘 pack 加载                   |
| `@dipper/agent`        | Runtime、会话、工具、packs、runners、Kernel/Product/Renderer facade |
| `@dipper/host-desktop` | 桌面 browser + OS 密钥能力                                       |
| `@dipper/host-cli`     | 文件/环境密钥（无 browser）                                         |

## 项目目录

```text
dipper-worker/
├── packages/          # @dipper/* 工作区包
│   ├── protocol/
│   ├── kernel/
│   ├── agent/
│   ├── host-desktop/
│   └── host-cli/
├── worker/            # Electron main / preload / IPC / 桌面适配
│   ├── agent/         # agent-bridge、agent-host、child-host、桌面 browser 工具
│   └── hosts/cli/     # embedded / child 库宿主
├── src/               # React UI（chat / sidebar / panel / settings / screenshot）
├── shared/            # 供 renderer 再导出的类型
├── examples/plugins/  # 工作区工具包示例
├── scripts/           # electron-dev / dist / clean / rasterize-icon
├── resources/         # 图标
├── skills/            # 随包技能
└── docs/              # PACKAGE / PROTOCOL / MODEL-DATA / PLUGINS / workflow
```

## 开发环境

- Node.js >= 20
- pnpm 11+

## 快速开始

```bash
cd dipper-worker
pnpm install
pnpm dev   # 构建 packages + electron main → Vite + Electron
```

## 脚本


| 命令                      | 说明                                                   |
| ----------------------- | ---------------------------------------------------- |
| `pnpm dev`              | 编译 packages/main + Vite + Electron 开发运行              |
| `pnpm build`            | 清理 dist → 构建 renderer + electron（含 `build:packages`） |
| `pnpm build:packages`   | 清理并构建 `@dipper/*` 包                                  |
| `pnpm typecheck`        | 构建 packages + TypeScript 检查                          |
| `pnpm icon:rasterize`   | 从 SVG 生成平台图标                                         |
| `pnpm dist`             | 图标 + 构建 + 按当前环境打包                                    |
| `pnpm dist:win`         | Windows x64：portable + NSIS                          |
| `pnpm dist:mac`         | macOS arm64：dmg + zip                                |
| `pnpm dist:linux`       | Linux x64：AppImage                                   |
| `pnpm dist:protected:*` | 混淆 electron 侧后打包（提高逆向门槛）                             |


打包细节见 [docs/zh_cn/PACKAGE.md](./docs/zh_cn/PACKAGE.md)。程序与模型数据见 [docs/zh_cn/MODEL-DATA.md](./docs/zh_cn/MODEL-DATA.md)。通讯协议见 [docs/zh_cn/PROTOCOL.md](./docs/zh_cn/PROTOCOL.md)。工作区插件见 [docs/zh_cn/PLUGINS.md](./docs/zh_cn/PLUGINS.md)。

## 许可证

Dipper Worker 使用 [MIT License](./LICENSE) 开源。

版权所有 © 2026 Dipper。保留所有权利。
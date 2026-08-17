# 插件开发与部署

工作区 **工具包插件（tool-pack）** 用于向 Agent 注册自定义工具。插件是工作区下的可信本地代码，安装在 `<workspace>/plugins/`，并在**共享的插件宿主子进程**中加载。

示例包：[`examples/plugins/echo-pack/`](../../examples/plugins/echo-pack/)。

## 概念

| 术语 | 含义 |
|------|------|
| **工具包（tool pack）** | 含 `manifest.json` + JS 入口、可注册若干工具的目录 |
| **packId** | 注册表装配键（全局唯一；不可占用内置 id） |
| **插件宿主** | 每个工作区一个 Node 子进程；该工作区下**所有**外部 pack 共用此进程 |
| **信任域** | 同一工作区内的 pack **互不隔离** |

外部 pack 不能覆盖内置 `packId`（`core`、`media`、`browser`、`content`），也不能注册与内置工具同名的工具。

## 安装位置

主路径：

```text
<workspace>/
  plugins/
    <任意目录名>/
      manifest.json
      index.js          # 或 manifest.entry 指定的相对路径
      …                 # 包内依赖 / 辅助文件
```

只会扫描 `plugins/` 下**直接子目录**中带 `manifest.json` 的文件夹，不会递归发现更深层 pack。

可选扫描根（工作区安装时通常不用）：

- 随包资源：`$DIPPER_RESOURCES_PATH/plugins` 或应用 `resources/plugins`
- 遗留全局：`~/.dipper-worker/plugins`（仅在显式 `includeGlobal` 时）

## Manifest

`manifest.json`（磁盘加载仅支持 `kind: "tool-pack"`）：

```json
{
  "id": "pack.example.echo",
  "kind": "tool-pack",
  "version": 1,
  "packId": "example-echo",
  "entry": "index.js",
  "description": "示例外部工具包",
  "requires": []
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 稳定唯一 id（如 `pack.vendor.name`） |
| `kind` | 是 | 磁盘加载必须为 `"tool-pack"` |
| `version` | 是 | 数字 |
| `packId` | 是 | 注册键；不可为 `core` / `media` / `browser` / `content` |
| `entry` | 否 | 相对包目录的 JS 路径；默认 `index.js` |
| `description` | 否 | 可读描述 |
| `requires` | 否 | 宿主能力总线必须具备的 capability id |

`entry` 不得通过 `..` 逃出包目录。

## 入口模块

入口在插件宿主子进程内以 **CommonJS** `require` 加载。任选一种导出方式：

1. `contribute(sink)`
2. `default` = `contribute` 函数，或 `{ contribute }` / 完整 plugin 对象
3. `createPlugin()` 返回 `{ manifest, contribute }`（若带 `manifest.packId`，必须与磁盘 `packId` 一致）

`sink` 与 `ToolRegistry` 一致：

```js
function contribute(sink) {
  sink.register({
    name: 'example_echo',
    description: '回显字符串。',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string', description: '要回显的文本' },
      },
      required: ['text'],
    },
    async execute(params, ctx) {
      return String(params.text ?? '')
    },
  })
  // 或：sink.registerAll([toolA, toolB])
}

module.exports = { contribute }
```

### 工具结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 暴露给模型的工具 id（唯一） |
| `description` | string | 供模型理解何时/如何使用 |
| `parameters` | object | JSON Schema（`type` / `properties` / `required`） |
| `meta` | 可选 | 见下方权限说明 |
| `execute` | `(params, ctx) => Promise<string>` | 返回值会字符串化后交给模型 |

### 宿主内的 `ctx`（ToolContext）

可序列化字段 + 回调到 Agent 进程的反向 RPC：

| 字段 | 说明 |
|------|------|
| `workspace` | 工作区绝对路径 |
| `restrictToWorkspace` | 路径限制开关 |
| `authorizedFolders` | 额外授权根目录 |
| `sessionId` / `locale` | 有则传入 |
| `signal` | 当前回合的 AbortSignal |
| `onProgress(tool, detail)` | 向 UI 推送进度 |
| `askPermission(...)` | 反向 RPC（可用时） |
| `askUser(prompt, options?)` | 反向 RPC（可用时） |
| `runSubagent({ description, prompt, … })` | 反向 RPC（可用时） |

子进程环境为**最小白名单**（PATH、区域设置、Dipper 路径提示等），**不会**转发父进程中的密钥 / API Key。会设置 `DIPPER_PLUGIN_HOST=1`。

## 权限

外部工具在父进程侧强制：

- `meta.permission.kind = 'plugin'`
- `alwaysConfirm = true`

因此每次调用都会确认（`plugin` 不会被会话级「始终允许」吞掉）。包内声明的 `meta.permission` / `parallelSafe` 不会取消该门控；子进程上报的 `parallelSafe` 会被忽略（经 IPC 串行执行）。

非交互运行时，`plugin` 权限会被拒绝。

## 生命周期

1. 打开工作区时绑定 `plugins/`，启动（或复用）共享宿主。
2. 各 pack 在子进程中 `require`；Agent 进程侧持有代理 Tool。
3. `plugins/` 下文件变更会在**空闲时热重载**（尽量按 pack 指纹做增量 sync）。
4. `reloadWorkspace()` 可强制刷新工作区（skills / workflows / plugins / config）。

单个 pack 加载失败会打警告并跳过，不影响其它 pack。同一宿主内工具名重复会导致该 pack 加载失败。

## 开发

1. 复制示例：

   ```bash
   cp -r examples/plugins/echo-pack <workspace>/plugins/my-pack
   ```

2. 修改 `manifest.json`（`id`、`packId`、`description`）与 `index.js`（工具 `name` 不得与内置或其它 pack 冲突）。

3. 优先使用纯 Node CommonJS。包目录下自带的 `node_modules` 只要可被入口解析即可。

4. 重新打开工作区或等待热重载；在日志中查找 `[plugins] loaded …` 或拒绝原因。

5. 在对话中让模型调用你的工具，或确认本回合工具列表已包含新工具。

### 命名建议

- `packId`：kebab-case，带命名空间（如 `acme-invoice`）。
- 工具 `name`：snake_case，在内置 + 同工作区全部 pack 中唯一（如 `acme_create_invoice`）。
- 勿覆盖内置名（`read_file`、`exec` 等）——加载器会拒绝该 pack。

## 部署

将 pack 视为**工作区本地安装物**（与工作区内其它代码同一信任级别）：

1. 将包构建/整理为含 `manifest.json` + 入口（及所需相对资源 / `node_modules`）的目录。
2. 复制到 `<workspace>/plugins/<pack-folder>/`。
3. 在 Dipper Worker 中打开该工作区（或触发重载）。确认日志中 `packId` 已被接受。
4. 分发时打包该目录（zip / git submodule / 内部制品）即可；接收方解压到目标工作区的 `plugins/`。

仓库内没有独立的远程插件市场安装路径：部署方式就是往工作区文件系统拷贝。

### 检查清单

- [ ] `kind` 为 `tool-pack`；已设置 `id` / `packId` / `version`
- [ ] `packId` 不在 `core` | `media` | `browser` | `content` 内
- [ ] 工具名不与内置或同工作区其它 pack 冲突
- [ ] 入口为 CommonJS，并导出 `contribute`（或等价形式）
- [ ] `execute` 返回字符串（或可干净字符串化的值）
- [ ] 不依赖父进程环境中的密钥
- [ ] 复制到目标工作区后已实测

## 安全说明

- Pack 对该工作区视为**可信代码**。
- 所有 pack 共用一个进程——恶意或有缺陷的 pack 可能影响同工作区其它 pack。
- 不要把不信任来源的 pack 装进敏感工作区。
- `execute` 中尽量最小权限（遵守 `restrictToWorkspace` / `authorizedFolders`；高风险操作走 `askPermission`）。

## 相关文档

- 协议与工具包总览：[PROTOCOL.md](./PROTOCOL.md) §5.3
- 示例：[`examples/plugins/echo-pack/`](../../examples/plugins/echo-pack/)
- 类型：`@dipper/protocol`（`PluginManifest`、`ToolPackPlugin`），`@dipper/agent`（`Tool`、`ToolContext`）
- 加载 / 注册：`@dipper/kernel`（`discoverPluginDirs`、`loadToolPackPluginFromDir`、`PluginRegistry`）

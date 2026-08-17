# 打包说明

基于 Electron + electron-builder。产物输出到 `release/`。

## 前置条件

1. 安装依赖：`pnpm install`
2. 图标：`resources/icon.svg`（`pnpm run icon:rasterize` 生成 `icon.png` / `icon.ico`）
3. 在目标平台本机打包（跨平台交叉编译能力有限）

## 常用命令

| 命令 | 说明 |
|------|------|
| `pnpm run icon:rasterize` | 从 SVG 生成平台图标 |
| `pnpm run build` | 仅构建（不打安装包） |
| `pnpm run dist` | 图标 + 构建 + 按当前环境打包 |
| `pnpm run dist:win` | Windows x64（portable + NSIS） |
| `pnpm run dist:mac` | macOS arm64（dmg + zip） |
| `pnpm run dist:linux` | Linux amd64（AppImage） |
| `pnpm run dist:protected:win` | 混淆 electron 侧后打 Windows x64 |
| `pnpm run dist:protected:mac` | 混淆 electron 侧后打 macOS arm64 |
| `pnpm run dist:protected:linux` | 混淆 electron 侧后打 Linux amd64 |

兼容别名：`package` / `package:win` / `package:mac` / `package:linux` → 对应 `dist*`。

### 按平台打包

```bash
# Windows：便携版 + 安装包
pnpm run dist:win

# macOS Apple Silicon
pnpm run dist:mac

# Linux amd64
pnpm run dist:linux
```

### 加固打包（混淆 electron 主进程 / UtilityProcess）

与普通打包同一平台目标，额外混淆 `dist/**/*.js`（**不混淆** renderer `dist/`）：

```bash
pnpm run dist:protected:win
pnpm run dist:protected:mac
pnpm run dist:protected:linux
```

| | `dist:win` / `dist:mac` / `dist:linux` | `dist:protected:*` |
|--|--|--|
| 平台 | 各自固定平台与架构 | 与对应普通命令相同 |
| 代码混淆 | 无 | 对 `dist/**/*.js` 混淆（跳过 builtin-skills） |
| 适用场景 | 日常分发 / 调试 | 对外分发、提高逆向门槛 |

说明：ASAR 与 Electron Fuses 由 `electron-builder.yml` 统一配置，普通打包也会启用。

### 产物示例

- `Dipper Worker-0.1.0-win-x64-portable.exe`（便携版）
- `Dipper Worker-0.1.0-win-x64-setup.exe`（NSIS 安装包）
- `Dipper Worker-0.1.0-mac-arm64.dmg`
- `Dipper Worker-0.1.0-linux-x64.AppImage`

版本号来自 `package.json` 的 `version`。

## 构建流水线

各 `dist*` 脚本大致流程：

1. `pnpm run icon:rasterize` — 生成图标
2. `pnpm run build` — 清理 dist → `build:packages`（`@dipper/*`）→ renderer + electron → `dist/`
3. （仅 `dist:protected:*`）`node scripts/obfuscate-electron.cjs` — 混淆 electron 侧 `dist/**/*.js`
4. `node scripts/dist.cjs […]` — 先清空 `release/`，再 electron-builder（配置：`electron-builder.yml`）

`pnpm run build:packages` 会执行 `scripts/clean-packages.mjs`，再构建 `protocol` → `kernel` → `agent` / `host-desktop` / `host-cli`。

`scripts/dist.cjs` 默认设置国内镜像，并优先使用本机已安装的 Electron（`node_modules/electron/dist`）：

- `ELECTRON_MIRROR` → npmmirror electron
- `ELECTRON_BUILDER_BINARIES_MIRROR` → npmmirror electron-builder-binaries

也可手动覆盖，例如 PowerShell：

```powershell
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"
pnpm run dist:win
```

## 打包配置摘要（electron-builder.yml）

- 输出目录：`release/`
- `asar: true`；native 相关模块 unpack
- `extraResources`：窗口图标、`skills/`
- Electron Fuses：关闭 `runAsNode` / 部分调试入口，启用 ASAR 完整性校验
- Windows：portable + NSIS，x64
- macOS：dmg + zip，arm64
- Linux：AppImage，x64

## OCR

- OCR 由内置 `skills/rapidocr` 技能提供（基于 `rapidocr-onnxruntime`，Python）。
- 检测/识别模型随 pip 包分发，安装后离线可用，覆盖简体中文 + 英文。
- 无需随应用打包语言包；首次使用时 agent 按技能说明安装依赖。

## 相关文件

- `package.json` — pnpm scripts（含 `build:packages`、`clean:packages`、`clean:dist`、`clean:release`）
- `packages/*` — `@dipper/protocol` / `kernel` / `agent` / `host-desktop` / `host-cli`
- `electron-builder.yml` — electron-builder 配置
- `scripts/dist.cjs` — 带镜像的打包入口（打包前清空 `release/`）
- `scripts/clean-packages.mjs` / `clean-dist.mjs` / `clean-release.mjs` — 构建清理
- `scripts/obfuscate-electron.cjs` — electron 侧混淆（protected）
- `scripts/rasterize-icon.mjs` — 图标生成

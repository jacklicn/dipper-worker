# Packaging Guide

Based on Electron + electron-builder. Artifacts go to `release/`.

## Prerequisites

1. Install dependencies: `pnpm install`
2. Icons: `resources/icon.svg` (`pnpm run icon:rasterize` generates `icon.png` / `icon.ico`)
3. Package on the target platform locally (cross-compilation support is limited)

## Common commands

| Command | Description |
|------|------|
| `pnpm run icon:rasterize` | Generate platform icons from SVG |
| `pnpm run build` | Build only (no installer) |
| `pnpm run dist` | Icons + build + package for current environment |
| `pnpm run dist:win` | Windows x64 (portable + NSIS) |
| `pnpm run dist:mac` | macOS arm64 (dmg + zip) |
| `pnpm run dist:linux` | Linux amd64 (AppImage) |
| `pnpm run dist:protected:win` | Obfuscate electron side, then package Windows x64 |
| `pnpm run dist:protected:mac` | Obfuscate electron side, then package macOS arm64 |
| `pnpm run dist:protected:linux` | Obfuscate electron side, then package Linux amd64 |

Compatibility aliases: `package` / `package:win` / `package:mac` / `package:linux` → corresponding `dist*`.

### Package by platform

```bash
# Windows: portable + installer
pnpm run dist:win

# macOS Apple Silicon
pnpm run dist:mac

# Linux amd64
pnpm run dist:linux
```

### Hardened packaging (obfuscate electron main / UtilityProcess)

Same platform targets as normal packaging, plus obfuscation of `dist/**/*.js` (**does not** obfuscate renderer `dist/`):

```bash
pnpm run dist:protected:win
pnpm run dist:protected:mac
pnpm run dist:protected:linux
```

| | `dist:win` / `dist:mac` / `dist:linux` | `dist:protected:*` |
|--|--|--|
| Platform | Fixed platform and arch each | Same as matching normal command |
| Code obfuscation | None | Obfuscate `dist/**/*.js` (skip builtin-skills) |
| When to use | Day-to-day distribution / debugging | External distribution, raise reverse-engineering bar |

Note: ASAR and Electron Fuses are configured in `electron-builder.yml` and also apply to normal packaging.

### Artifact examples

- `Dipper Worker-0.1.0-win-x64-portable.exe` (portable)
- `Dipper Worker-0.1.0-win-x64-setup.exe` (NSIS installer)
- `Dipper Worker-0.1.0-mac-arm64.dmg`
- `Dipper Worker-0.1.0-linux-x64.AppImage`

Version comes from `package.json` `version`.

## Build pipeline

Each `dist*` script roughly:

1. `pnpm run icon:rasterize` — generate icons
2. `pnpm run build` — clean dist → `build:packages` (`@dipper/*`) → renderer + electron → `dist/`
3. (`dist:protected:*` only) `node scripts/obfuscate-electron.cjs` — obfuscate electron `dist/**/*.js`
4. `node scripts/dist.cjs […]` — clears `release/`, then electron-builder (config: `electron-builder.yml`)

`pnpm run build:packages` runs `scripts/clean-packages.mjs` then builds `protocol` → `kernel` → `agent` / `host-desktop` / `host-cli`.

`scripts/dist.cjs` defaults to China mirrors and prefers a locally installed Electron (`node_modules/electron/dist`):

- `ELECTRON_MIRROR` → npmmirror electron
- `ELECTRON_BUILDER_BINARIES_MIRROR` → npmmirror electron-builder-binaries

You can override manually, e.g. PowerShell:

```powershell
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"
pnpm run dist:win
```

## Packaging config summary (electron-builder.yml)

- Output directory: `release/`
- `asar: true`; native-related modules unpacked
- `extraResources`: window icons, `skills/`
- Electron Fuses: disable `runAsNode` / some debug entry points; enable ASAR integrity check
- Windows: portable + NSIS, x64
- macOS: dmg + zip, arm64
- Linux: AppImage, x64

## OCR

- OCR is provided by the built-in `skills/rapidocr` skill (based on `rapidocr-onnxruntime`, Python).
- Detection/recognition models ship with the pip package; offline after install; covers Simplified Chinese + English.
- No language packs need to ship with the app; on first use the agent installs dependencies per the skill docs.

## Related files

- `package.json` — pnpm scripts (includes `build:packages`, `clean:packages`, `clean:dist`, `clean:release`)
- `packages/*` — `@dipper/protocol` / `kernel` / `agent` / `host-desktop` / `host-cli`
- `electron-builder.yml` — electron-builder config
- `scripts/dist.cjs` — packaging entry with mirrors (clears `release/` first)
- `scripts/clean-packages.mjs` / `clean-dist.mjs` / `clean-release.mjs` — build cleans
- `scripts/obfuscate-electron.cjs` — electron-side obfuscation (protected)
- `scripts/rasterize-icon.mjs` — icon generation

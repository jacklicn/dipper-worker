# Plugin Development & Deployment

Workspace **tool-pack plugins** add custom tools the agent can call. They are trusted local code under `<workspace>/plugins/`, loaded into a shared plugin-host child process.

Sample pack: [`examples/plugins/echo-pack/`](../examples/plugins/echo-pack/).

## Concepts

| Term | Meaning |
|------|---------|
| **Tool pack** | A folder with `manifest.json` + a JS entry that registers one or more tools |
| **packId** | Assembly key used by the registry (must be unique; cannot reuse builtin ids) |
| **Plugin host** | One Node child process per workspace; **all** external packs in that workspace share it |
| **Trust domain** | Packs in the same workspace are **not** isolated from each other |

External packs cannot override builtin `packId`s (`core`, `media`, `browser`, `content`) or builtin tool names.

## Install location

Primary path:

```text
<workspace>/
  plugins/
    <any-folder-name>/
      manifest.json
      index.js          # or path in manifest.entry
      …                 # pack-local deps / helpers
```

Discovery scans immediate subdirectories of `plugins/` that contain `manifest.json`. Nested packs are not discovered.

Optional roots (usually off for workspace installs):

- Bundled: `$DIPPER_RESOURCES_PATH/plugins` or app `resources/plugins`
- Legacy global: `~/.dipper-worker/plugins` (only when explicitly enabled via `includeGlobal`)

## Manifest

`manifest.json` (kind must be `tool-pack`):

```json
{
  "id": "pack.example.echo",
  "kind": "tool-pack",
  "version": 1,
  "packId": "example-echo",
  "entry": "index.js",
  "description": "Sample external tool pack",
  "requires": []
}
```

| Field | Required | Notes |
|-------|----------|--------|
| `id` | yes | Stable unique id (e.g. `pack.vendor.name`) |
| `kind` | yes | Must be `"tool-pack"` for disk loading |
| `version` | yes | Number |
| `packId` | yes | Registry key; not `core` / `media` / `browser` / `content` |
| `entry` | no | Relative JS path under the pack dir; default `index.js` |
| `description` | no | Human-readable |
| `requires` | no | Capability ids that must be present on the host bus |

`entry` must stay inside the pack directory (no `..` escape).

## Entry module

The entry is loaded with **CommonJS** `require` inside the plugin-host child. Export one of:

1. `contribute(sink)`
2. `default` = `contribute` function or `{ contribute }` / full plugin object
3. `createPlugin()` returning `{ manifest, contribute }` (if `manifest.packId` is set, it must match disk `packId`)

`sink` matches `ToolRegistry`:

```js
function contribute(sink) {
  sink.register({
    name: 'example_echo',
    description: 'Echo a string.',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string', description: 'Text to echo' },
      },
      required: ['text'],
    },
    async execute(params, ctx) {
      return String(params.text ?? '')
    },
  })
  // or: sink.registerAll([toolA, toolB])
}

module.exports = { contribute }
```

### Tool shape

| Field | Type | Notes |
|-------|------|--------|
| `name` | string | Unique tool id exposed to the model |
| `description` | string | When/what for the model |
| `parameters` | object | JSON Schema (`type` / `properties` / `required`) |
| `meta` | optional | See permissions below |
| `execute` | `(params, ctx) => Promise<string>` | Return value is stringified for the model |

### `ctx` (ToolContext) in the host

Serializable fields plus bridges back to the agent process:

| Field | Notes |
|-------|--------|
| `workspace` | Absolute workspace path |
| `restrictToWorkspace` | Path policy flag |
| `authorizedFolders` | Extra allowed roots |
| `sessionId` / `locale` | When present |
| `signal` | Abort for the enclosing turn |
| `onProgress(tool, detail)` | Live progress to UI |
| `askPermission(...)` | Reverse RPC (if available) |
| `askUser(prompt, options?)` | Reverse RPC (if available) |
| `runSubagent({ description, prompt, … })` | Reverse RPC (if available) |

Child env is a **minimal** allowlist (PATH, locale, Dipper path hints). Parent secrets / API keys are **not** forwarded. `DIPPER_PLUGIN_HOST=1` is set.

## Permissions

For external tools, the parent forces:

- `meta.permission.kind = 'plugin'`
- `alwaysConfirm = true`

So each call prompts (no session “always allow” for `plugin`). Declaring `meta.permission` / `parallelSafe` in the pack does not disable that gate; `parallelSafe` from the child is ignored (IPC stays serial).

In non-interactive runs, `plugin` permissions are rejected.

## Lifecycle

1. Opening a workspace binds `plugins/` and starts (or reuses) the shared host.
2. Each pack is `require`’d in the child; tools are proxied in the agent process.
3. File changes under `plugins/` trigger **idle hot-reload** (incremental sync by pack fingerprint when possible).
4. `reloadWorkspace()` forces a full workspace refresh (skills / workflows / plugins / config).

Failed packs are skipped with a console warning; other packs still load. Duplicate tool names inside the shared host fail that pack’s load.

## Develop

1. Copy the sample:

   ```bash
   cp -r examples/plugins/echo-pack <workspace>/plugins/my-pack
   ```

2. Edit `manifest.json` (`id`, `packId`, `description`) and `index.js` (tool `name`s must not collide with builtins or other packs).

3. Prefer plain Node CommonJS. Pack-local `node_modules` under the pack directory are fine if resolvable from the entry.

4. Restart the workspace or wait for hot-reload; check agent logs for `[plugins] loaded …` / rejection messages.

5. Ask the model to call your tool, or verify via a chat turn that lists tools.

### Naming tips

- `packId`: kebab-case, namespaced (`acme-invoice`).
- Tool `name`: snake_case, unique across builtins + all workspace packs (`acme_create_invoice`).
- Avoid shadowing builtins (`read_file`, `exec`, …) — the loader rejects those packs.

## Deploy

Treat packs as **workspace-local install artifacts** (same trust as other workspace code):

1. Build/bundle your pack to a folder containing `manifest.json` + entry (and any relative assets / `node_modules` you need).
2. Copy into `<workspace>/plugins/<pack-folder>/`.
3. Open that workspace in Dipper Worker (or trigger reload). Confirm logs show the `packId` accepted.
4. Distribute by shipping the folder (zip / git submodule / internal package). Recipients unpack under their workspace `plugins/`.

There is no separate remote plugin marketplace install path in-tree: deployment is filesystem copy into the workspace.

### Checklist

- [ ] `kind` is `tool-pack`; `id` / `packId` / `version` set
- [ ] `packId` not in `core` | `media` | `browser` | `content`
- [ ] Tool names do not collide with builtins or other packs in the same workspace
- [ ] Entry is CommonJS and exports `contribute` (or equivalent)
- [ ] `execute` returns a string (or value that stringifies cleanly)
- [ ] No reliance on parent env secrets inside the child
- [ ] Pack tested under the target workspace after copy

## Security notes

- Packs run as **trusted** code for that workspace.
- All packs share one process — a malicious or buggy pack can affect others in the same workspace.
- Do not install packs from untrusted sources into a sensitive workspace.
- Prefer least privilege in `execute` (respect `restrictToWorkspace` / `authorizedFolders`; use `askPermission` for risky ops).

## Related

- Protocol / tool packs overview: [PROTOCOL.md](./PROTOCOL.md) §5.3
- Sample: [`examples/plugins/echo-pack/`](../examples/plugins/echo-pack/)
- Types: `@dipper/protocol` (`PluginManifest`, `ToolPackPlugin`), `@dipper/agent` (`Tool`, `ToolContext`)
- Loader / registry: `@dipper/kernel` (`discoverPluginDirs`, `loadToolPackPluginFromDir`, `PluginRegistry`)

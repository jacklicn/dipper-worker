---
name: mcp-manager
description: Guide for connecting, verifying, enabling, disabling, and managing MCP (Model Context Protocol) servers from chat — stdio (local process), Streamable HTTP, and legacy SSE transports. Use when the user asks to add/remove/enable/disable/test an MCP server, enable tools from an MCP registry, or troubleshoot why an MCP server's tools are missing.
---

# MCP Server Management

This skill explains how to connect and manage MCP servers from chat using the
dedicated `mcp_add` / `mcp_remove` / `mcp_enable` / `mcp_disable` / `mcp_list` /
`mcp_test` tools. No manual file editing is needed.

## When to use

- The user says "add/connect/enable an MCP server", "use the X MCP", or pastes
  an MCP server URL/registry page.
- A configured MCP server's tools are missing or fail to connect.
- The user asks what MCP servers are configured, or wants to turn one off/on.
- The user asks to disable a server temporarily without removing its config.

## Workflow

### 1. Identify the transport

Ask what the server is, or infer from the URL/registry:

| Transport | Use when | Example |
|---|---|---|
| `stdio` | A local process must be spawned (`npx`, `node`, `python`) | `npx -y @modelcontextprotocol/server-github` |
| `streamable-http` / `http` | A remote endpoint that accepts POST JSON-RPC | `https://api.example.com/mcp` |
| `sse` | A legacy endpoint with `GET /sse` + messages URL | `https://old-server.com/sse` |

If unsure, prefer `streamable-http` for remote URLs and `stdio` for local
commands.

### 2. Register with `mcp_add`

Call `mcp_add` with:

- `name` — short unique id, e.g. `github`, `postgres`, `docs`.
- `type` — `stdio` | `streamable-http` | `http` | `sse`.
- stdio: `command` (+ optional `args`, `env`, `cwd`).
  - Windows-friendly: use `npx` and the tool resolves `npx.cmd` automatically.
- http/sse: `url` (+ optional `headers`, e.g. `Authorization`).
- `enabled` — optional boolean (default `true`). Set `false` to register a
  server without connecting it yet.

The tool saves the config, rebuilds tools, connects, and reports the exposed
tool list — including any connection error.

### 3. Enable / disable

- `mcp_enable <name>` turns a disabled server back on; it reconnects and its
  tools reappear on the next tool rebuild.
- `mcp_disable <name>` keeps the config but stops the server; its tools
  disappear on the next tool rebuild. Use this when a server should stay
  registered but be turned off (e.g. an unused or flaky endpoint).
- `mcp_list` shows each server's transport and `[enabled]` / `[disabled]`
  status.

### 4. Verify

- After `mcp_add` succeeds, list the tools it exposed and confirm they appear.
- If the user later reports tools missing, call `mcp_list` to see configured
  servers, then `mcp_test <name>` to re-verify connectivity.
- After a config change, the new/removed tools take effect on the next chat
  turn (the runtime rebuilds the tool registry).

### 5. Clean up

- `mcp_remove <name>` removes a server entirely; its tools disappear on the
  next rebuild.
- `mcp_list` shows the current configuration for quick reference.

## Notes

- MCP tools are exposed to the model under `mcp__<server>__<tool>` names.
- Remote servers may require auth headers — pass them in `headers`.
- `mcp_test` refuses to probe a disabled server; `mcp_enable` it first.
- Connection/verification failures return the underlying error text so you can
  help the user fix auth, URL, or command issues.

---
name: download
description: "Use for any network file download task — the default download path: installers, archives, large binaries, torrent/magnet/metalink, or fetching a file over http(s). Prefer the built-in download_url tool — it drives the bundled naria2 engine first (multi-connection, resumable, P2P/metalink capable) and falls back to the built-in Node stream downloader automatically. Triggers include: download, 下载, fetch file, get installer, torrent, magnet, .torrent, metalink, curl/wget download."
---

# Download — built-in naria2 engine, built-in fallback

## When to use

Use **`download_url`** (built-in tool) for every network file download —
it is the **default download path**. This includes: installers, archives,
large binaries, `.torrent`, magnet links, and `.meta4`/`.metalink`. Do **not**
shell out to `curl`, `wget`, `Invoke-WebRequest`, or a system `aria2c`, and do
**not** hand-roll downloads in scripts (`urllib`/`requests`/`fetch`/`axios`) —
the built-in tool already provides the fastest and most robust path.

Also use `download_url` (not `curl`) when you need to **save a remote page's raw
bytes** (HTML, image, JSON, etc.) to a file on disk — e.g. a web page you want to
keep for later analysis. For merely reading page text in-context, use
`web_fetch` instead.

## Engine priority

1. **naria2 engine (first choice)** — the bundled `aria2c` binary, driven by
   `download_url`. Supports:
   - http(s) with multi-connection split (up to 16 connections, resumable)
   - magnet / `.torrent` (BitTorrent with DHT + peer exchange)
   - `.meta4` / `.metalink` (multi-mirror)
2. **Built-in Node stream downloader (automatic fallback)** — used when the
   naria2 engine cannot start (missing/unpackable binary, RPC unreachable) or a
   transfer fails. Supports http(s) single- or multi-stream; P2P/metalink have
   **no** fallback, so keep `download_url` — its `engine` field in the result
   tells you which path was used (`naria2` or `builtin`).

You do not need to do anything special for the fallback — `download_url`
handles engine choice internally and reports it in the result.

## How to call

```json
{"url": "https://example.com/app.zip", "path": "downloads/app.zip", "connections": 8}
```

- `url` — http(s), magnet, `.torrent`, or `.meta4`/`.metalink`.
- `path` — destination. For **http(s)** this is the **file path**; for
  **magnet/torrent/metalink** it is the **containing directory** (default
  `downloads/`).
- `filename` — override the name for http(s) when `path` is a directory or
  omitted.
- `connections` — parallel connections for range-capable servers (1–16, default
  8); P2P peers are capped separately. Raise it for large files, lower for
  small ones.

## Conventions

- **Always save under `downloads/`** by default (never `outputs/` or
  `uploads/`) unless the user asks otherwise.
- Prefer keeping the URL exactly as given; do not add mirrors unless the user
  asks (the app picks domestic mirrors automatically for Node/Python packages
  in the Chinese UI).
- For installers you then need to run, still put them in `downloads/` and run
  from there (or copy into `outputs/` first only if you must modify them).

## Troubleshooting

- Result says `engine: builtin` → naria2 was unavailable for this transfer;
  this is expected behavior, not an error.
- P2P error mentioning "requires the aria2 engine" → a magnet/torrent/metalink
  could not start at all; report the error message, do not try `curl`/`wget`.
- Large/slow transfer → raise `connections` (cap 16) and let progress stream;
  do not start a second parallel download of the same file.

## After completion

- Tell the user the relative path and final size.
- For P2P/metalink downloads, mention how many files landed under the
  directory.

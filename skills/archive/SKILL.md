---
name: archive
description: >-
  Use this skill for archive tasks: extract (unpack), list, test, and create
  archives in zip, 7z, rar, tar, gzip, xz, bzip2, and other formats. The worker
  bundles the 7-Zip binary — call the built-in `archive` tool (no system install
  needed). Triggers include 解压, 压缩, extract, unzip, unpack, unrar, 7z,
  decompress, create archive, zip a folder, list archive contents, test archive.
license: MIT (bundled 7-Zip binary via 7zip-bin-full)
---

# Archive — bundled 7-Zip (zip/7z/rar/tar/gz/xz)

## When to use

Use this skill whenever the user wants to work with archive files: extracting /
unpacking, listing contents, verifying integrity, or creating archives. Covers
**zip**, **7z**, **rar** (extract only), **tar**, **tar.gz / tgz**, **xz**,
**bzip2 / tar.bz2**, **cab**, **iso**, **wim**, **arj**, and many other
formats.

**How to call**: use the built-in `archive` tool. Do **not** use `exec` to shell
out to system `unzip` / `7z` / `tar` / `WinRAR` — the bundled binary already
covers all these formats with one tool.

## Tool usage

The `archive` tool takes a JSON object:

- `operation` (required): `extract` | `list` | `create` | `test`
- `archive` (required): workspace-relative path to the archive file.
- `output_dir`: extract destination (default `outputs/<basename>/`).
- `files_to_add`: for `create` — workspace-relative paths to pack.
- `type`: for `create` — `zip`, `7z`, `tar`, `gzip`, `xz`, `bzip2`, `wim`
  (inferred from the archive extension when omitted).
- `password`: for encrypted archives / creating encrypted archives.
- `overwrite`: for extract (default true).
- `files`: for extract — only unpack matching entries (paths or wildcards).
- `level`: for create — compression level 0-9 (default 5).

All paths are workspace-relative and sandboxed by the tool. Confirm the exact
archive path with `list_dir` / `glob` before calling.

**User confirmation**: all `archive` operations (`extract`, `create`, `list`,
`test`) require user approval before running — the app will always ask. Mention
what you are about to do (which archive, and where files go) before calling so
the confirmation is expected. If the user declines, stop and ask how to
proceed.

## Common task examples

**Extract a zip/7z/rar into outputs/**
```json
{"operation": "extract", "archive": "downloads/app.zip", "output_dir": "outputs/app"}
```

**List contents (read-only, no extraction)**
```json
{"operation": "list", "archive": "downloads/app.rar"}
```

**Verify integrity**
```json
{"operation": "test", "archive": "downloads/app.7z"}
```

**Create a zip from files/dirs**
```json
{"operation": "create", "archive": "outputs/bundle.zip", "files_to_add": ["outputs/a.txt", "outputs/data/"], "type": "zip"}
```

**Extract only some entries (e.g. markdown docs)**
```json
{"operation": "extract", "archive": "downloads/kit.zip", "output_dir": "outputs/kit", "files": ["docs/*.md"]}
```

**Extract an encrypted archive**
```json
{"operation": "extract", "archive": "downloads/secret.7z", "output_dir": "outputs/secret", "password": "<ask user>"}
```

**Create a tar.gz from a directory**
```json
{"operation": "create", "archive": "outputs/backup.tar.gz", "files_to_add": ["outputs/project/"]}
```

## Format notes

- **rar is read-only** — the open-source 7-Zip build cannot create rar archives.
- `.tar.gz` / `.tgz` and `.tar.xz` / `.tar.bz2` are handled automatically; for
  `create`, the compression type is inferred from the extension.
- Readable formats include (full-feature binary): 7z, zip, tar, gzip, xz,
  bzip2, **rar/rar5**, cab, iso, wim, arj, lzh, cpio, rpm, deb, zstd, and
  disk-image formats (ext, fat, ntfs, vhd, vhdx, qcow2, vmdk, dmg, …).
- Create formats: 7z, zip, tar, gzip, xz, bzip2, wim.
- For zip with many small files, raising `level` to 9 shrinks size at the cost
  of speed; for large binary blobs, `level` 1 (store) is fastest.
- Encrypted archives: always ask the user for the password (or let them know an
  encrypted archive needs one) — never guess it.

## Troubleshooting

- `archive not found` → wrong path or outside the workspace; run `list_dir` /
  `glob` first to confirm the exact filename (watch out for non-ASCII names).
- `wrong password` / `password required` → ask the user for the correct
  password and retry.
- Large archives → extraction may take a while; let progress stream and do not
  start parallel extractions of the same archive.
- Nested archives (e.g. a tar inside a zip) → extract the outer one first, then
  extract the inner archive from its output path.

## After completion

- Tell the user the relative output directory and how many files were
  extracted.
- For `create`, report the archive path and size.
- Clean up unneeded intermediate files with `delete_file` (only under
  `outputs/` etc.).

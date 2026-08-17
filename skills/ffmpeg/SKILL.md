---
name: ffmpeg
description: >-
  Use this skill for any media processing task: audio/video/image conversion,
  transcode, extracting audio from video, frame extraction, GIF creation,
  resizing/formatting images, probing media info, cutting/merging clips,
  adding subtitles or watermarks. The worker bundles a static ffmpeg binary —
  call the built-in `ffmpeg` tool (no system install needed). Triggers include
  transcode, convert audio/video, extract audio, cut a clip, compress media,
  convert mp3, make a GIF, probe media info.
license: GPL-3.0-or-later (bundled ffmpeg binary via ffmpeg-static)
---

# FFmpeg — bundled audio/video/image processing

## When to use

Use this skill whenever the user asks to process media files (audio, video,
images), including but not limited to: format conversion, transcode/compression,
extracting audio from video, cutting clips, merging/concat, frame extraction,
GIF creation, image resize/format conversion, adding subtitles or watermarks,
and probing media information.

**How to call**: use the built-in `ffmpeg` tool (its description notes the host
system). Pass the **complete ffmpeg argument list** via the `args` array — the
program only supplies the static binary (no system install required). Do not
use `exec` to shell out to a system ffmpeg.

## Tool usage

- The `ffmpeg` tool takes one `args` parameter (array of strings) plus an
  optional `timeout_sec`.
- Inputs follow `-i <path>`; the last non-flag argument is the output file.
- All paths are sandboxed to the workspace + authorized folders (the tool
  validates them).
- The output is not overwritten by default; pass `-y` when needed.
- Add `-progress pipe:3` to stream live progress.
- To probe a file use `["-i","file"]` — the info prints to stderr and an exit
  code of 1 is expected.

## Common task examples

**Audio: extract MP3 from video with a target bitrate**
```json
{"args": ["-i", "a.mp4", "-vn", "-c:a", "libmp3lame", "-b:a", "192k", "out.mp3"]}
```

**Audio: extract to WAV (lossless PCM)**
```json
{"args": ["-i", "a.mp4", "-vn", "-c:a", "pcm_s16le", "out.wav"]}
```

**Audio: cut a clip (keep the first 30 seconds)**
```json
{"args": ["-i", "a.mp3", "-t", "30", "-c", "copy", "clip.mp3"]}
```

**Audio: take 10 seconds starting at 1:00**
```json
{"args": ["-ss", "00:01:00", "-i", "a.mp3", "-t", "10", "-c", "copy", "clip.mp3"]}
```

**Video: compress to H.264**
```json
{"args": ["-i", "a.mov", "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-pix_fmt", "yuv420p", "out.mp4"]}
```

**Video: remove audio track**
```json
{"args": ["-i", "a.mp4", "-an", "-c:v", "copy", "silent.mp4"]}
```

**Video: extract frames (1 frame per second)**
```json
{"args": ["-i", "a.mp4", "-vf", "fps=1", "frame_%03d.jpg"]}
```

**Video: make a GIF**
```json
{"args": ["-i", "a.mp4", "-vf", "fps=10,scale=480:-1", "out.gif"]}
```

**Image: convert / compress format**
```json
{"args": ["-i", "photo.png", "-q:v", "85", "photo.jpg"]}
```

**Image: resize**
```json
{"args": ["-i", "photo.png", "-vf", "scale=800:-1", "small.png"]}
```

**Concat: two audio/video files (same codec)**
```json
{"args": ["-i", "a.mp4", "-i", "b.mp4", "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1", "merged.mp4"]}
```

**Burn subtitles**
```json
{"args": ["-i", "a.mp4", "-vf", "subtitles=sub.srt", "subbed.mp4"]}
```

## Encoder availability (important)

The bundled binary is statically compiled, so **available encoders depend on
the build** (the Windows binary is the essentials build; Linux/macOS builds
differ). Choose arguments according to the host system:

- Prefer universal encoders: `libx264` for video, `libmp3lame` / `aac` /
  `pcm_s16le` for audio, JPEG/PNG for images.
- On `Unknown encoder`, do not trial-and-error — switch to the universal
  encoders above, or list available encoders first with `ffmpeg -encoders`.
- Use `-pix_fmt yuv420p` for H.264 (browser/player compatibility); when
  optimizing GIFs with `palettegen`/`paletteuse`, note that filters depend on
  the build.

## Platform & path notes

- The tool receives a plain argument array and does **not** go through a shell,
  so paths with spaces, non-ASCII characters, or `&` need no manual escaping —
  but the path must resolve inside the workspace (confirm with `list_dir` /
  `glob` first).
- Output defaults to the workspace (prefer `outputs/`). ffmpeg usually handles
  non-ASCII paths on Windows directly; if a path fails, run once with
  `-loglevel error` and read the exact error.
- For long jobs (large video, high resolution), set `timeout_sec` (default 300,
  max 3600) and add `-progress pipe:3` to watch progress; do not run several
  large transcodes in parallel.

## Troubleshooting

- `exit=1` with only `-i` → expected; the info is on stderr — parse it.
- `No such file or directory` → wrong path or outside the workspace; run
  `list_dir` first.
- `Unknown encoder` → not available in this build; switch to a universal
  encoder.
- Output missing with exit 0 is rare; it is usually accompanied by a later
  error — read the full stderr.
- If the subtitle filter cannot find the font file, check the path and font
  name (escape `:` and `\` on Windows).
- Probe with `-i` once before guessing parameters, to avoid blind argument
  selection.

## After completion

- Tell the user the output file path (relative to the workspace).
- For large files, compare sizes before/after and state how much space was
  saved.
- Clean up unneeded intermediate artifacts (temp mp3/wav) with `delete_file`
  (only under `outputs/` etc.).

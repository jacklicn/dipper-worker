# Dipper Worker User Manual

**Software Name:** Dipper Worker (AI Worker)  
**Version:** V1.0.1  
**Document Type:** User Operation Manual  
**Audience:** End users

Chinese: [docs/zh_cn/USER-MANUAL.md](./zh_cn/USER-MANUAL.md).

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation and Launch](#3-installation-and-launch)
4. [Interface Overview](#4-interface-overview)
5. [First-Time Setup](#5-first-time-setup)
6. [Workspace Management](#6-workspace-management)
7. [Session Management](#7-session-management)
8. [AI Chat](#8-ai-chat)
9. [Built-in Browser](#9-built-in-browser)
10. [Files Panel](#10-files-panel)
11. [Built-in Terminal](#11-built-in-terminal)
12. [Screenshot and Annotation](#12-screenshot-and-annotation)
13. [Settings](#13-settings)
14. [Permissions and Security](#14-permissions-and-security)
15. [Self-Learning and Memory](#15-self-learning-and-memory)
16. [Workspace Plugins](#16-workspace-plugins)
17. [System Tray and Window](#17-system-tray-and-window)
18. [Keyboard Shortcuts](#18-keyboard-shortcuts)
19. [FAQ](#19-faq)

---

## 1. Introduction

### 1.1 Overview

Dipper Worker is a desktop AI collaboration assistant. Through natural language conversation, users can perform file operations, run code, search the web, automate browsers, recognize text in images, generate documents, and more. The app also provides a built-in browser, terminal, files panel, screenshot annotation, and other desktop collaboration tools within a local workspace.

### 1.2 Key Features

- **Simple:** Add a workspace, configure an AI provider and model, then start chatting. Built-in catalog of 20 major model providers with one-click selection and automatic model list fetching.
- **Efficient:** Agent dispatches built-in tool packs and optional workspace plugins; background learning deposits memory and reusable skills over time.
- **Reliable:** API keys encrypted via OS secure storage; permission gates, authorized folders, path guards, and network guards; local session persistence.
- **Economical:** Pure local desktop app with no subscription or middleman service; automatic token budgeting and long-session compaction.

### 1.3 About This Manual

This manual describes installation, configuration, and daily operations for Dipper Worker V1.0.1. UI labels in this document follow the English interface where noted; switch language in Settings → Appearance.

---

## 2. System Requirements

### 2.1 Hardware

| Item | Minimum | Recommended |
|------|---------|-------------|
| CPU | 64-bit dual-core | Quad-core or better |
| RAM | 4 GB | 8 GB or more |
| Disk | 500 MB free | 2 GB or more |
| Display | 1280×720 | 1920×1080 or higher |

### 2.2 Software

| Platform | Supported versions |
|----------|-------------------|
| Windows | Windows 10 / 11 (x64) |
| macOS | Apple Silicon (arm64) |
| Linux | x64 with AppImage support |

### 2.3 Network

- Internet required when using cloud LLM APIs (requests go directly to your configured endpoint).
- The app does not host conversation data on Dipper servers.
- Local models may work without external network depending on deployment.

---

## 3. Installation and Launch

### 3.1 Distribution Packages

| Platform | Type | Example filename |
|----------|------|----------------|
| Windows | Portable | `Dipper Worker-1.0.1-win-x64-portable.exe` |
| Windows | Installer | `Dipper Worker-1.0.1-win-x64-setup.exe` |
| macOS | DMG | `Dipper Worker-1.0.1-mac-arm64.dmg` |
| Linux | AppImage | `Dipper Worker-1.0.1-linux-x64.AppImage` |

### 3.2 Windows Installation

**Installer (NSIS):**

1. Double-click `Dipper Worker-1.0.1-win-x64-setup.exe`.
2. Follow the wizard to choose an install directory and complete setup.
3. Launch from the Start menu or desktop shortcut.

**Portable:**

1. Copy `Dipper Worker-1.0.1-win-x64-portable.exe` to any folder.
2. Double-click to run without installation.

### 3.3 macOS Installation

1. Open `Dipper Worker-1.0.1-mac-arm64.dmg`.
2. Drag Dipper Worker into Applications.
3. Launch from Applications; allow in System Settings → Privacy & Security if prompted.

### 3.4 Linux Installation

1. Download the AppImage.
2. `chmod +x Dipper\ Worker-1.0.1-linux-x64.AppImage`
3. Double-click or run from terminal.

### 3.5 First Launch

1. Only one instance runs at a time (single-instance lock).
2. Welcome screen prompts to add a workspace and configure AI.
3. Closing the main window keeps the app in the system tray (see Chapter 17).

---

## 4. Interface Overview

### 4.1 Layout

The main window has the following regions:

```
┌─────────────────────────────────────────────────────────────┐
│  Title bar (drag · minimize / maximize / close)             │
├─────────────┬────────────────────────────────┬──────────────┤
│             │                                │              │
│  Sidebar    │    Center area                 │  Icon rail   │
│             │ (Chat or Settings)             │  · Browser   │
│  Workspace  │                                │  · Files     │
│  Sessions   │                                │  · Terminal  │
│             │                                │  · Settings  │
│  Account    │                                │              │
│             │                                │  ┌──────────┐│
│             │                                │  │Side panel││
│             │                                │  └──────────┘│
└─────────────────────────────────────────────────────────────┘
```

- **Title bar** — drag to move; minimize, maximize, close
- **Left sidebar** — session search, pinned sessions, workspace and session list, account menu
- **Center** — chat or settings view
- **Right icon rail** — browser, files, terminal, settings
- **Side panel** — slides in for browser, files, or terminal

### 4.2 Resizing

- Drag handles between sidebar, center, and side panel to resize columns.
- Side panel header: Maximize expands the panel; Close hides it.

---

## 5. First-Time Setup

### 5.1 Add a Workspace

1. On the welcome screen, click **Add workspace**, or click **+** next to Workspaces in the sidebar.
2. Choose a local folder in the system dialog.
3. Confirm; the workspace appears in the sidebar.

### 5.2 Configure AI Provider

1. Open **Settings** (gear on icon rail) or **Configure AI** from welcome.
2. Go to **AI Provider**.
3. Select a built-in vendor or **Custom**.
4. Enter **API Key**, **API Base**, and **Model**; refresh model list if needed.
5. Click **Save & Apply**.

### 5.3 First Chat

1. Click **+** or **New Chat** in the sidebar.
2. Type a task in the composer at the bottom.
3. Press **Enter** to send (default).
4. Review the agent reply and any permission prompts.

---

## 6. Workspace Management

### 6.1 Expand / Collapse

Click the workspace name or chevron to show or hide the session list.

### 6.2 Rename

Workspace **⋯** menu → **Edit name** → confirm.

### 6.3 Appearance

Click the color circle: pick a color, choose a photo, or reset to automatic.

### 6.4 Open Folder

**⋯** menu → **Open Folder** — opens the workspace root in the file manager.

### 6.5 Change Workspace

**⋯** menu → **Change workspace** — pick a new folder; old files remain on disk.

### 6.6 Remove Workspace

**⋯** menu → **Remove** — removes from sidebar only; does not delete disk files.

### 6.7 Workspace Directories

| Path | Purpose |
|------|---------|
| `sessions/` | Session and message data |
| `memory/` | User preferences and memory notes |
| `skills/` | Reusable skills |
| `workflows/` | Reusable workflows |
| `uploads/` | User attachments |
| `downloads/` | Downloaded files |
| `outputs/` | Agent outputs and tool results |
| `plugins/` | Workspace plugins |
| `.dipper-worker/` | Groups, permissions, authorized dirs, appearance |

Global config (including secrets) lives in `~/.dipper-worker/`.

---

## 7. Session Management

### 7.1 New Chat

Click **+** on the workspace or group header.

### 7.2 Switch Session

Click a session row in the sidebar.

### 7.3 Pin / Unpin

Pin icon or session **⋯** menu → **Pin** / **Unpin**.

### 7.4 Rename, Archive, Delete

Session **⋯** menu: **Edit name**, **Archive** / **Unarchive**, **Delete** (with confirmation).

### 7.5 Groups

- Create: workspace **⋯** → **New group…**
- Move: drag session to group, or **Move to group** in session menu
- Delete group: removes all sessions in the group (confirmed)

### 7.6 Search

**Ctrl+Shift+F** (Mac: **⌘⇧F**) — search sessions and messages; **↑↓** navigate, **Enter** open, **Esc** close.

### 7.7 Load More

Click **Load more** at the bottom of the session list when available.

---

## 8. AI Chat

### 8.1 Send Message

Type in the composer; click the up-arrow or press **Enter** (configurable to **Ctrl+Enter**).

### 8.2 Stop Generation

Click the square **Stop** button while the agent is responding.

### 8.3 Queue While Busy

- **Enter** — queue message for after current turn
- **Ctrl+Enter** — interrupt and send immediately
- Manage queue above the composer: reorder, remove, **Send now**

### 8.4 Attachments

- Paperclip → file picker
- Drag and drop onto composer
- Paste images from clipboard
- Screenshot (Chapter 12) or camera icon in composer

Attachments are saved under `uploads/`.

### 8.5 Model Selector

Composer toolbar — override model per session or **Use default**.

### 8.6 Edit / Delete Messages

Right-click user bubble: **Edit**, **Delete**, **Copy**, **Select All**.

### 8.7 Find in Conversation

**Ctrl+F** (Mac: **⌘F**) — find bar with **Enter** / **Shift+Enter** for next/previous match.

### 8.8 Permission and Question Prompts

Inline cards during chat:

- **Reject** / **Allow once** / **Always allow** for permissions
- Option buttons or text input for agent questions; **Revise request** to edit original task

### 8.9 Tool Activity

Expandable entries show tool name, arguments summary, and results.

---

## 9. Built-in Browser

Open from the **Browser** icon on the icon rail.

| Feature | How to use |
|---------|------------|
| Tabs | **+** new tab; click tab to switch; close button on tab |
| Navigation | Back, Forward, Reload/Stop |
| Address bar | URL, local path, or search — **Enter** to go |
| Local file | Folder icon → pick HTML or image |
| Favorites | Star to add; hub for search, folders, pin, dock |
| More (⋯) | Open in system browser, Clear cache, Favorites |

Default start page: Bing. Agent browser usage shows a red dot on the icon until you open the panel.

---

## 10. Files Panel

Open from the **Files** icon.

Lists workspace root (cannot be removed) and additional **authorized folders** from Settings.

Click **Open Folder** to open a directory in the system file manager.

File actions in messages: Open, Download, Copy Path, Reveal in Explorer/Finder, Add to Chat (images: preview, zoom, rotate).

---

## 11. Built-in Terminal

Open from the **Terminal** icon.

Integrated xterm shell; default cwd is the active workspace root.

Toolbar: **New** (+), **Restart**, **Copy**, **Select All**, **Kill session**.

---

## 12. Screenshot and Annotation

**Trigger:** Default **Alt+Q** (Settings → Shortcuts), or camera icon in composer.

1. Drag to select region (**Esc** cancel).
2. Annotate: rectangle, ellipse, arrow, brush, mosaic, eraser, text, eyedropper.
3. **Undo** (**Ctrl+Z**), **Download**, **Cancel**, **Complete** (**Enter**).

Complete from composer attaches image to the pending message.

---

## 13. Settings

Entry: icon rail **Settings**, account menu, or setup CTAs. **Back to app** or **Esc** to leave.

| Section | Items |
|---------|-------|
| Overview | Status, runtime, model, config path, quick links |
| Appearance | Language (System / 中文 / English), Theme (System / Light / Dark) |
| Shortcuts | Send key mode, screenshot key, reset defaults |
| AI Provider | Vendor, API Key, API Base, Model, Save & Apply, Delete |
| Agent Parameters | Max Tokens, Temperature, Max Tool Iterations |
| Permissions | Authorized folders — add / remove (root cannot be removed) |
| Advanced | Safety toggle, runtime info, repair workspace, open folder |

---

## 14. Permissions and Security

- API keys stored in OS secure storage (`secrets.json`); redacted in UI and config APIs.
- Permission gates for commands, files, browser, MCP, and dangerous operations.
- Authorized folders and path guards limit file access.
- Network guards reduce SSRF risk.
- Conversation data stays local; LLM requests go directly to your `apiBase`.

---

## 15. Self-Learning and Memory

After each turn, background learning may deposit:

| Type | Location |
|------|----------|
| User preferences | `memory/USER.md` |
| Project notes | `memory/` |
| Skills | `skills/*/SKILL.md` |
| Workflows | `workflows/*/WORKFLOW.md` |

Low-confidence results are discarded. Logs: `.dipper-worker/learning.jsonl`. See `docs/workflow/` for workflow format.

---

## 16. Workspace Plugins

Install tool-pack plugins under `<workspace>/plugins/<pack>/` with `manifest.json` and entry JS.

Copy a plugin folder into `plugins/`; hot-reload on idle or reopen workspace. Cannot override builtin pack IDs or tool names. See [PLUGINS.md](./PLUGINS.md).

---

## 17. System Tray and Window

- Close window → app stays in tray
- Tray click/double-click → show window
- Tray menu → Show window, Quit AI Worker
- Single instance only
- Account menu: Zoom In (**Ctrl++**), Zoom Out (**Ctrl+-**), Actual Size (**Ctrl+0**)

---

## 18. Keyboard Shortcuts

| Shortcut | Action | Configurable |
|----------|--------|--------------|
| Ctrl+B / ⌘B | Toggle sidebar | No |
| Ctrl+Shift+F / ⌘⇧F | Session search | No |
| Ctrl+F / ⌘F | Find in conversation | No |
| Enter / Ctrl+Enter | Send message | Yes |
| Shift+Enter | New line in composer | — |
| Alt+Q (default) | Screenshot | Yes |
| Ctrl++/⌘+ | Zoom in | No |
| Ctrl+-/⌘- | Zoom out | No |
| Ctrl+0/⌘0 | Actual size | No |
| Esc | Close dialogs, settings, find, screenshot | Context |
| Ctrl+Z/⌘Z | Undo annotation | Screenshot mode |

---

## 19. FAQ

**Status shows Not ready** — Configure AI Provider with valid API Key, Base, and Model.

**Agent errors** — Check network, API quota, and model name; try another model.

**Frequent permission prompts** — Use **Always allow** in chat (dangerous ops still prompt) or add authorized folders in Settings.

**Reopen after close** — Click the tray icon.

**Session data location** — `<workspace>/sessions/` and `~/.dipper-worker/`.

**Change language** — Settings → Appearance → Language.

**Fully quit** — Tray menu → Quit AI Worker.

---

## Appendix: Document History

| Version | Date | Notes |
|---------|------|-------|
| V1.0.1 | 2026-08 | Initial release for Dipper Worker V1.0.1 |

---

Copyright © 2026 Dipper. All rights reserved.

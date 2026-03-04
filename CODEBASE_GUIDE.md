# Phantom — Codebase Deep Dive Guide

> **Purpose**: Read this file to quickly understand the entire browser-automation codebase.
> Last updated: 2026-03-04

---

## What Is This App?

**Phantom** is an autonomous browser automation agent built by **NinjaTech AI**. It receives tasks from humans via Slack, controls a real Chromium browser to complete them, and reports results back. Think of it as a personal web assistant that can do anything you can do in a browser — search, fill forms, extract data, manage accounts, take screenshots, etc.

### How It Works (Big Picture)

```
You (Slack) ──task──▶ Monitor ──▶ Orchestrator ──▶ Claude Code (brain)
                                                        │
                                                        ▼
                                                  Phantom Toolkit
                                                  (observe → think → act)
                                                        │
                                                        ▼
                                                  Real Chromium Browser
                                                  (persistent, with VNC)
                                                        │
                                                        ▼
                                              Results ──▶ Slack (screenshots, text)
```

### Deployment Target

Designed to run inside a **NinjaTech AI sandbox** — a containerized environment with:
- Virtual display (Xvfb) for headed browser
- VNC for live browser viewing
- Supervisord managing all services
- LiteLLM gateway for AI model access
- Psiphon proxy for network access

Can also run locally with reduced functionality (no VNC, no sandbox URLs).

---

## File Map (Every File Explained)

```
browser-automation/
├── orchestrator.py          # ENTRY POINT — launches Claude Code as the agent brain
├── monitor.py               # Slack poller — watches for mentions, triggers responses
├── slack_interface.py       # Slack API wrapper (CLI + Python API, 2800+ lines)
├── browser_interface.py     # Playwright wrapper — all browser interactions go through here
├── agents_config.py         # Agent identity registry (just Phantom for now)
├── claude-wrapper.sh        # Bash wrapper for Claude CLI (pseudo-TTY, output sanitization)
├── tavily_client.py         # Web research tools (search, extract, crawl, map, research)
├── requirements.txt         # Python deps: playwright, flask, boto3, mcp, requests, etc.
├── install.sh               # Full setup: deps, playwright, psiphon, supervisord, patches
├── settings.json            # Auto-generated: ANTHROPIC_AUTH_TOKEN, BASE_URL, MODEL
│
├── phantom/                 # === BROWSER AUTOMATION TOOLKIT ===
│   ├── observer.py          # "Eyes" — screenshots + accessibility tree + element extraction
│   ├── actions.py           # "Hands" — click, fill, scroll, extract + self-healing selectors
│   ├── browser_server.py    # Persistent Chromium manager (start/stop/status on port 9222)
│   ├── config.py            # Config dataclass (model, viewport, timeouts, max_steps)
│   ├── presets.py           # 7 task templates (screenshot, search, extract, pdf, etc.)
│   ├── vnc.py               # VNC URL generation + human help requests via Slack
│   ├── stealth.py           # Anti-bot JS patches (hide webdriver, fake plugins, etc.)
│   ├── session_health.py    # Login session checker (Google, LinkedIn, Twitter, GitHub, etc.)
│   └── tests/               # Tests for toolkit modules
│
├── agent-docs/              # === DOCUMENTATION (loaded into Claude's prompt) ===
│   ├── PHANTOM_SPEC.md      # Phantom's full behavior spec — THE key doc
│   ├── AGENT_PROTOCOL.md    # Slack communication rules and message formats
│   ├── SLACK_INTERFACE.md   # Slack CLI tool reference
│   ├── LITELLM_GUIDE.md     # LiteLLM gateway usage guide
│   └── MODELS.md            # Available AI models catalog
│
├── utils/                   # === SHARED AI UTILITIES ===
│   ├── litellm_client.py    # Gateway config (reads settings.json, resolves model aliases)
│   ├── chat.py              # chat(), chat_json(), chat_stream() — text generation
│   ├── images.py            # generate_image() — image generation (gemini-image, gpt-image)
│   ├── video.py             # generate_video() — video generation (sora, sora-pro)
│   ├── embeddings.py        # embed(), cosine_similarity() — text embeddings
│   └── mcp.py               # MCP tool discovery and calling via LiteLLM gateway
│
├── dashboard/               # === WEB DASHBOARD ===
│   └── app.py               # Flask app (port 9000) — agent info, logs, token/cost stats
│
├── supervisor/              # === PROCESS MANAGEMENT ===
│   └── supervisord.conf     # Manages: Xvfb, x11vnc, noVNC, browser, psiphon, dashboard
│
├── memory/                  # === PERSISTENT AGENT MEMORY ===
│   └── phantom_memory.md    # Updated after each task with learned site knowledge
│
├── avatars/                 # Agent avatar images for Slack
│   └── phantom.png
│
├── reports/                 # Task execution reports
├── logs/                    # Execution logs (daily rotating)
│
# Runtime temp files (outside repo):
# /tmp/phantom_batch_dedup/  — Per-thread message counters for anti-duplicate guard
# /root/.agent_settings.json — Slack channel + agent config (created by setup.sh)
```

---

## Core Components — How They Work

### 1. Orchestrator (`orchestrator.py`)

**The entry point.** Launches Claude Code as the Phantom agent.

**Two modes:**
- `python orchestrator.py` — **Work loop**: spawns two parallel processes (work agent + monitor)
- `python orchestrator.py --task "Do X"` — **Single task**: runs once and exits

**What it does on startup:**
1. Checks single-instance lock (`.orchestrator.lock` with heartbeat)
2. Loads agent identity from `~/.agent_settings.json`
3. Auto-generates `settings.json` from `~/.claude/settings.json` credentials
4. Optionally logs into GitHub CLI via `/dev/shm/mcp-token`
5. Builds a prompt that includes: agent identity, spec docs, memory, task
6. Runs `claude-wrapper.sh -c -p <prompt>` (15-min timeout per invocation)

**Work loop architecture:**
```
Main Process
  ├── Process 1 (Work): Runs Claude Code for initialization tasks (MUST NOT use slack_interface.py)
  └── Process 2 (Monitor): Runs monitor.py — exclusive Slack watcher, batches mentions → Claude
```

> **Important:** The Monitor process is the sole Slack listener. The Work process handles initialization (reading spec, verifying browser connectivity, updating memory) but **must NEVER use `slack_interface.py` in any way** — not to read, send, or respond to messages. This prevents duplicate replies. When the Monitor detects a mention, it invokes Claude Code via `claude-wrapper.sh` with `PHANTOM_BATCH_MODE=1` set in the environment.

**Key configs:**
- Lock file: `.orchestrator.lock` (PID + heartbeat, 10-min staleness timeout)
- Logs: `/workspace/logs/{agent}_{date}.log`
- Model selection: reads from `/dev/shm/sandbox_metadata.json`, falls back to `claude-opus-4-6`

---

### 2. Monitor (`monitor.py`)

**Slack watcher.** Polls every ~60s for mentions and thread replies, batches them, sends to Claude.

**Poll cycle:**
1. Fetch last 20 messages from Slack channel (single API call)
2. Check each message for agent mentions (case-insensitive text match)
3. Check threads with activity — auto-respond to replies on agent's own messages
4. Batch ALL pending messages into one prompt
5. Invoke Claude via `claude-wrapper.sh` (180s timeout)
6. Save seen-message state to disk

**Key features:**
- Rate limiting: exponential backoff (60s → 120s → 240s → ... → 600s max)
- Deduplication: tracks seen messages in `.seen_messages.json` (last 100)
- Thread tracking: stores agent's own messages in `.agent_messages.json` (last 20)
- Audio support: detects voice messages, passes to Claude for Whisper transcription
- Max runtime: 24 hours, then exits
- **Batch mode**: Sets `PHANTOM_BATCH_MODE=1` env var when invoking Claude, which enables the anti-duplicate guard in `slack_interface.py`

**Anti-duplicate guard (`PHANTOM_BATCH_MODE`):**
When the monitor spawns Claude for a batch response, it sets `PHANTOM_BATCH_MODE=1`. This activates the `_check_batch_dedup()` guard in `slack_interface.py`, which:
- Tracks how many messages have been sent per thread (via `/tmp/phantom_batch_dedup/`)
- Allows up to 4 messages per thread (ack + results + caption + buffer)
- Silently blocks any additional messages (returns fake success so Claude doesn't retry)
- The monitor cleans the dedup directory before each new batch cycle

**Message batching format sent to Claude:**
```
--- Message 1 (mention) ---
From: username | Time: ts | Text: content
Thread: thread_ts (reply with: python slack_interface.py say "message" -t {thread_ts})

--- Message 2 (thread_reply) ---
From: username | Time: ts | Text: content
Thread: thread_ts (reply with: python slack_interface.py say "message" -t {thread_ts})
```

All replies are threaded under the original message (both channel mentions and thread replies).

---

### 3. Slack Interface (`slack_interface.py`) — ~2800 lines

**Full Slack integration.** Both CLI tool and Python API.

**Class hierarchy:**
- `SlackConfig` — persisted settings (`~/.agent_settings.json`): channel, agent, workspace, token
- `SlackTokens` — token container (bot tokens only, user tokens rejected)
- `SlackClient` — low-level API calls with retry (5 retries, exponential backoff, token refresh)
- `SlackInterface` — high-level Python API (`say()`, `upload_file()`, `get_history()`, etc.)

**Token resolution order:**
1. Cached in `~/.agent_settings.json`
2. `/dev/shm/mcp-token` (auto-populated by sandbox "Connect" button)
3. Environment: `SLACK_BOT_TOKEN` or `SLACK_MCP_XOXB_TOKEN`

**Agent impersonation:** Messages are sent with custom username + avatar URL. Five agents defined (nova, pixel, bolt, scout, phantom) — only phantom is active.

**CLI commands:**
```bash
python slack_interface.py config --set-channel "#ch" --set-agent phantom
python slack_interface.py say "message"           # Send as agent
python slack_interface.py read -l 50              # Read channel
python slack_interface.py upload file.png         # Upload file
python slack_interface.py channels / users / history / scopes / join / create
```

**Notable features:**
- S3-backed caching (reduces Slack API calls ~70-80%, 2-min TTL)
- Markdown → Slack mrkdwn conversion
- Sandbox URL conversion (`0.0.0.0:8080` → public sandbox URL)
- 3-step file upload (get URL → upload → complete)

---

### 4. Browser Interface (`browser_interface.py`)

**Playwright wrapper.** All browser interactions go through this class.

**Two connection modes:**

| Mode | Method | Use Case |
|------|--------|----------|
| **CDP** | `BrowserInterface.connect_cdp()` | Connect to persistent browser (Phantom's normal mode) |
| **Local** | `BrowserInterface().start()` | Launch fresh browser (testing, one-off scripts) |

**CDP mode (primary):**
- Connects to browser on `http://localhost:9222`
- Health-checks `/json/version` endpoint first
- Closes stale `about:blank` tabs via `_close_default_tabs()` before creating a new context (prevents a second browser window)
- Reuses existing tabs and cookies
- Viewport set to 1600x900 to match Xvfb
- `stop()` only disconnects — browser keeps running
- Stealth patches auto-applied on connect

**Full method inventory:**

| Category | Methods |
|----------|---------|
| Navigation | `goto()`, `reload()`, `go_back()`, `go_forward()` |
| Properties | `title`, `url`, `content` |
| Click/Hover | `click()`, `double_click()`, `right_click()`, `hover()` |
| Forms | `fill()`, `type_text()`, `press()`, `select_option()`, `check()`, `uncheck()` |
| Extract | `text()`, `html()`, `attribute()`, `query_all()`, `query_texts()`, `evaluate()` |
| Screenshots | `screenshot()`, `pdf()` |
| Wait | `wait_for()`, `wait_for_url()`, `wait_for_load()`, `sleep()` |
| Tabs | `new_tab()`, `close_tab()`, `tab_count` |
| Scroll | `scroll_down()`, `scroll_up()`, `scroll_to()`, `scroll_to_top()`, `scroll_to_bottom()` |
| Cookies | `cookies()`, `set_cookie()`, `clear_cookies()`, `local_storage()` |
| Network | `block_resources()`, `intercept_requests()` |
| DevTools | `console_logs()`, `js_errors()`, `network_errors()`, `error_report()` |
| Stealth | `check_stealth()` (auto-applied, no manual setup) |
| Sessions | `check_session()`, `session_status()`, `vnc_url()` |

**DevTools capture:** Automatically collects console logs, JS errors, and network failures during browsing. Access via `error_report()` or `assert_no_errors()`.

---

### 5. Phantom Toolkit (`phantom/`)

#### 5a. Observer (`phantom/observer.py`) — "The Eyes"

Captures full page state in one call: `observe(browser, step, screenshot=True)`

**What it returns:**
```python
{
    "url": "https://...",
    "title": "Page Title",
    "screenshot_path": "phantom/screenshots/step_000.png",
    "screenshot_b64": "base64...",           # For vision analysis
    "accessibility_tree": "...",              # Compact page structure (6 levels deep)
    "interactive_elements": [...],            # Up to 100 clickable/fillable elements
    "has_overlay": True/False,                # Cookie banner/popup detected
    "errors": "..." or None,                  # JS/network errors from DevTools
}
```

**Screenshot pipeline:**
1. Wait for page to settle (domcontentloaded + networkidle)
2. Extract interactive elements via JS (buttons, links, inputs, etc.)
3. Inject Set-of-Mark (SoM) labels — numbered red badges on each element (max 50)
4. Take screenshot (with badges visible)
5. Remove badges
6. Build accessibility tree
7. Detect overlays (cookie banners, modals)

**Interactive elements include multiple selector candidates** for self-healing:
```python
{"index": 0, "tag": "input", "id": "search", "selector": "#search",
 "selectors": ["#search", "input[name='q']", "input[type='text']"], ...}
```

#### 5b. Actions (`phantom/actions.py`) — "The Hands"

Executes browser actions with self-healing selectors.

**Usage pattern:**
```python
set_elements(observation["interactive_elements"])  # Load element context
result = execute_action(browser, "click", {"selector": "#submit"})
```

**26 actions:** goto, click, fill, type_text, press, select_option, check, hover, dismiss_overlay, go_back, go_forward, reload, scroll_*, extract_*, execute_js, wait, wait_for_element, screenshot, save_pdf, get_cookies, clear_cookies, done, fail, need_human

**Self-healing selector system:**
1. Try primary selector
2. If fails → try cached selector (from previous success on same page)
3. If fails → try alternative selectors from interactive elements list
4. Supports `[0]`, `[1]` index references to SoM-labeled elements
5. Caches successful fallbacks per page (cleared on navigation)

**Overlay dismissal:** Tries 20+ common dismiss selectors (cookie accept, modal close, X buttons), falls back to Escape key.

#### 5c. Browser Server (`phantom/browser_server.py`)

Manages persistent Chromium on port 9222 (CDP).

```bash
python -m phantom.browser_server start    # Launch (background daemon)
python -m phantom.browser_server status   # PID, version, open tabs
python -m phantom.browser_server stop     # Graceful shutdown
python -m phantom.browser_server restart  # Stop + start
```

- Browser data persists in `phantom/browser_data/` (cookies, cache, sessions)
- Psiphon proxy always enabled (`127.0.0.1:18080`)
- 70+ Chromium flags for containerized environment
- PID tracked in `.browser_server.pid`

#### 5d. Config (`phantom/config.py`)

Dataclass with defaults → JSON override → env var override:

| Setting | Default | Env Var |
|---------|---------|---------|
| model | claude-sonnet-4-6 | PHANTOM_MODEL |
| max_steps | 30 | PHANTOM_MAX_STEPS |
| headless | False | PHANTOM_HEADLESS |
| viewport | 1600x900 | — |
| timeout | 30000ms | PHANTOM_TIMEOUT |
| proxy | None | PHANTOM_PROXY |

#### 5e. Presets (`phantom/presets.py`)

7 task templates: `screenshot`, `extract`, `extract_links`, `search` (Bing), `fill_form`, `pdf`, `monitor`

```python
task = get_preset_task("search", query="AI news 2026")
```

#### 5f. VNC (`phantom/vnc.py`)

Generates public VNC URLs for the sandbox:
```
https://6080-{sandbox_id}.app.super.{stage}myninja.ai/vnc.html?autoconnect=true
```

Functions: `get_vnc_url()`, `share_vnc_link(reason)`, `request_human_help(reason, page_url)`

#### 5g. Stealth (`phantom/stealth.py`)

7 JavaScript patches injected automatically on every page load:
1. Hide `navigator.webdriver` → `undefined`
2. Fake `chrome.runtime` → present
3. Fix `navigator.permissions` API
4. Populate `navigator.plugins` (3 fake plugins)
5. Set `navigator.languages` → `['en-US', 'en']`
6. Remove CDP artifacts (`cdc_*`, `__webdriver_*`, `__selenium_*`)
7. Spoof WebGL vendor/renderer → NVIDIA

#### 5h. Session Health (`phantom/session_health.py`)

Monitors login sessions by inspecting Chrome's SQLite cookie database.

**6 services:** Google, LinkedIn, Twitter, GitHub, Amazon, Facebook

Each has required cookie names and minimum count. Returns `valid` (bool), `cookies_found`, `cookies_missing`, `earliest_expiry`.

```bash
python phantom/session_health.py status          # Check all
python phantom/session_health.py check google    # Check one
python phantom/session_health.py monitor 30      # Continuous (every 30 min)
```

---

### 6. Utils (`utils/`)

Shared AI model utilities — all talk to the **LiteLLM gateway**.

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `litellm_client.py` | `get_config()`, `resolve_model()`, `api_url()` | Gateway config, model aliases |
| `chat.py` | `chat()`, `chat_json()`, `chat_stream()` | Text generation with any LLM |
| `images.py` | `generate_image()`, `generate_images()` | Image generation (gemini-image recommended) |
| `video.py` | `generate_video()` | Video generation (sora/sora-pro, async poll) |
| `embeddings.py` | `embed()`, `cosine_similarity()` | Text embeddings (1536 or 3072 dims) |
| `mcp.py` | `MCPClient.list_tools()`, `.call_tool()` | MCP tool discovery + calling |

**Model aliases:** `claude-opus`, `claude-sonnet`, `claude-haiku`, `gpt-5`, `gemini-pro`, `gemini-image`, `gpt-image`, `sora`, `sora-pro`, `embed-small`, `embed-large`, plus `ninja-*` variants.

---

### 7. Tavily Client (`tavily_client.py`)

Web research without browser, via MCP tools through LiteLLM gateway.

| Method | Speed | Best For |
|--------|-------|----------|
| `search(query)` | ~1s | Quick lookups, finding URLs |
| `extract(urls)` | ~2-5s | Reading specific pages |
| `crawl(url)` | ~5-15s | Crawling entire doc sites |
| `map(url)` | ~2-5s | Discovering URL structure |
| `research(topic)` | ~30-60s | Deep multi-source reports |

---

### 8. Dashboard (`dashboard/app.py`)

Flask web app on port 9000. Shows:
- Agent identity and status
- Real-time log streaming (SSE)
- Claude Code session stats (tokens, costs, tool usage)
- Recent prompts and responses

Parses Claude's JSONL session files directly for token/cost tracking. Uses Claude Opus 4 pricing ($15/$75 per M tokens input/output).

---

### 9. Infrastructure

#### `install.sh`
Full setup: Python deps → Playwright browsers → Psiphon proxy → supervisord config → platform patches → log dirs.

#### `supervisor/supervisord.conf`
Manages all services with dependency ordering:
```
Xvfb (:99) → x11vnc (:5901) → noVNC (:6081)
Browser (CDP :9222) + Psiphon (:18080)
Dashboard (:9000)
Platform services (http_server, browser_api, ttyd, code_server, MCP servers)
```

#### `claude-wrapper.sh`
Runs Claude CLI with pseudo-TTY (`script` command), passes `settings.json`, sanitizes ANSI output.

---

## Key Architectural Decisions

1. **Persistent browser** — Chromium runs as a background server. Tabs, cookies, and login sessions survive across tasks. Connect via CDP, never launch fresh.

2. **Claude Code as brain** — No hardcoded agent loop. Claude reads the spec, plans, and calls observer/actions directly. The LLM IS the planner.

3. **Self-healing selectors** — Actions try multiple selector strategies and cache successes. Handles sites that change DOM structure.

4. **Set-of-Mark (SoM) labels** — Observer overlays numbered badges on interactive elements so the LLM can reference them by index (`[0]`, `[3]`).

5. **Observe → Think → Act loop** — Agent always observes the page state before acting. Never guesses what's on screen.

6. **Human handoff** — Agent requests help via Slack + VNC link when hitting CAPTCHAs, login walls, or 2FA.

7. **Stealth by default** — Anti-bot patches applied automatically on every page load and new tab.

8. **Slack as the sole interface** — All human ↔ agent communication happens through Slack. No other UI needed.

---

## Port Map

| Port | Service | Purpose |
|------|---------|---------|
| 9222 | Chromium CDP | Browser remote debugging |
| 5901 | x11vnc | VNC server |
| 6080 | noVNC (websockify) | Browser-based VNC viewer |
| 9000 | Dashboard | Web UI for monitoring |
| 18080 | Psiphon HTTP | HTTP proxy |
| 18081 | Psiphon SOCKS | SOCKS proxy |
| 2222 | ttyd | Web terminal |
| 4000 | code-server | VS Code in browser |

---

## Common Workflows

### Run the agent (full loop)
```bash
python orchestrator.py
```

### Run a single task
```bash
python orchestrator.py --task "Search Google for NinjaTech AI"
```

### Test system readiness
```bash
python orchestrator.py --test
```

### Manual browser control
```python
from browser_interface import BrowserInterface
from phantom.observer import observe
from phantom.actions import execute_action, set_elements

browser = BrowserInterface.connect_cdp()
browser.goto("https://example.com")
obs = observe(browser, step=0)
set_elements(obs["interactive_elements"])
execute_action(browser, "click", {"selector": "#some-button"})
browser.stop()  # Disconnect only — browser keeps running
```

### Check login sessions
```bash
python phantom/session_health.py status
```

### Slack communication
```bash
python slack_interface.py say "Hello from Phantom!"
python slack_interface.py read -l 20
python slack_interface.py upload screenshot.png --title "Results"
```

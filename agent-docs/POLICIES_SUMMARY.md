# Agent Documentation — Policy Summary

> Quick-reference of all policies, rules, and guidelines across the ninja-squad documentation.
> **Last verified:** All policies tested and confirmed working.

---

## 1. Project Initialization & Workflow Order

**Source:** ARCHITECTURE.md, AGENT_PROTOCOL.md, ONBOARDING.md

| Rule | Description |
|------|-------------|
| **Nova starts first** | Nova must complete onboarding → interview stakeholders → write PRD → create GitHub issues → assign to agents — before any other agent begins work |
| **Other agents wait** | Pixel, Bolt, Scout must verify PRD exists (`agent-docs/PRD.md`) and GitHub issues are assigned (`gh issue list --assignee @me`) before starting |
| **No work without tasks** | Agents must NOT start work without assigned GitHub issues. If none exist, post in Slack asking Nova and WAIT |
| **WAKE UP instruction** | When any agent receives "WAKE UP" → run `python orchestrator.py` |
| **Orchestrator required** | After onboarding, all agents must run `python orchestrator.py` to start their work + monitor processes |

---

## 2. Onboarding (All Agents)

**Source:** ONBOARDING.md

| Step | Action | Critical? |
|------|--------|-----------|
| 1 | `pip install -r requirements.txt` — install dependencies (requests, slackify-markdown, boto3, playwright, mcp, httpx) | ⚠️ **Mandatory** — Slack interface fails without it |
| 2 | Read all docs in `agent-docs/` (own spec, ARCHITECTURE, AGENT_PROTOCOL, SLACK_INTERFACE, DEPLOYMENT, MODELS, LITELLM_GUIDE) | Yes |
| 2b | Review AI Models & Utility Library — verify `utils/` and gateway connectivity (`python -m utils.litellm_client`) | Yes |
| 2c | Verify Tavily Web Research Tools — run `python tavily_client.py` to confirm 5 tools work | Yes |
| 3 | Setup GitHub repo via `python scripts/setup_github.py owner/repo-name` — ASK user if repo not specified | Yes |
| 4 | Test Slack connection: `python slack_interface.py scopes` — ASK user to connect if not working | Yes |
| 5 | Configure Slack defaults: `config --set-channel` and `config --set-agent` — ASK user for values | Yes |
| 6 | Test capabilities: read messages, send test message, check GitHub, list files | Yes |
| 7 | Read memory file: `memory/<agent>_memory.md` | Yes |
| 8 | (Non-Nova) Check prerequisites: PRD exists + issues assigned | Yes |
| 9 | Verify Agent Dashboard running on port 9000: `supervisorctl status agent-dashboard` | Yes |
| 10 | Announce ready status in Slack | Yes |
| 11 | Call `complete` tool with dashboard URL to signal onboarding finished | ⚠️ **Mandatory** |

---

## 3. Never Assume — Always Ask

**Source:** ONBOARDING.md

| Policy | Detail |
|--------|--------|
| **Use `ask` tool** | When requirements are unclear, information is missing, decisions affect the user, or confirmation is needed |
| **Never guess** | Do not assume user preferences, project requirements, technical decisions, file locations, or config values |
| **Ask before acting** | Ask before sending messages to channels, making config changes, or choosing between options |
| **Bad practice** | Assuming defaults, guessing preferences, making decisions without confirmation, proceeding with missing info |

---

## 4. Communication Protocol

**Source:** AGENT_PROTOCOL.md, SLACK_INTERFACE.md

### Channel Rules
| Rule | Detail |
|------|--------|
| **Single primary channel** | All agent + human communication happens in one configured channel |
| **Keep messages SHORT** | 2-4 sentences max. No walls of text. Be direct and concise |
| **Always reply in threads** | Responses to questions/requests go in threads (`-t thread_ts`), never as new top-level messages |
| **Sprint updates** | One top-level "Session N Update 🧵" post per session — all agents reply in that thread with their updates |
| **No duplicate updates** | Don't create new top-level messages for updates. Find the existing Session thread and reply there |
| **Mention protocol** | Always @mention relevant agents. Use `@nova` for escalations. `@channel` only for emergencies |
| **Response expectations** | During sync: respond within window. Blockers: respond ASAP |

### Message Identity
| Rule | Detail |
|------|--------|
| **Agent identity required** | `say` command requires a configured agent (`config --set-agent`) |
| **Four agents** | Nova (🌟 PM), Pixel (🎨 UX), Bolt (⚡ Dev), Scout (🔍 QA) |
| **Custom avatars** | Bot token sends with agent name + avatar icon URL |
| **Stakeholders** | Human collaborators are product owners — all agents take orders from them |

### Escalation to Stakeholders
| When | Action |
|------|--------|
| Conflicting requirements | Escalate to stakeholders |
| Major technical decisions | Escalate with options + recommendation |
| Unresolvable blockers | Escalate with impact description |
| Significant changes need approval | Escalate with deadline |

---

## 5. File Sharing Policy

**Source:** AGENT_PROTOCOL.md

| Rule | Detail |
|------|--------|
| **All files go to the repo** | Designs → `designs/`, Code → repo, Docs → `docs/`, Reports → `reports/` |
| **Upload to Slack** | Upload files to Slack so team can view immediately |
| **Post GitHub link** | After committing, share the GitHub link in Slack for version-controlled reference |
| **Both required** | Files must be accessible in Slack (quick viewing) AND in the repo (version control) |

---

## 6. GitHub Workflow

**Source:** AGENT_PROTOCOL.md, ARCHITECTURE.md, BOLT_SPEC.md

| Rule | Detail |
|------|--------|
| **Issues first** | Nova creates all GitHub issues with clear acceptance criteria |
| **Assignment** | Design → @pixel, Development → @bolt, QA → @scout |
| **PR workflow** | Create PR with clear description → request review → address feedback |
| **Reference issues** | Always reference issue numbers in commits and Slack messages |
| **Labels & milestones** | Nova adds labels and milestones to issues |

---

## 7. Deployment & Networking

**Source:** DEPLOYMENT.md

### URL Pattern
| Component | Value |
|-----------|-------|
| **Pattern** | `https://<PORT>-<SANDBOX_ID>.app.super.<STAGE>myninja.ai` |
| **Metadata file** | `/dev/shm/sandbox_metadata.json` |
| **Fields** | `environment` (stage), `thread_id` (sandbox ID) |

### Binding Rules
| Rule | Detail |
|------|--------|
| **Always bind to `0.0.0.0`** | Never `127.0.0.1` or `localhost` — proxy can't reach localhost-only services |
| **Never use localhost in frontend** | Browser runs on user's machine, not in sandbox — use public URL |
| **CORS required** | Frontend and backend are different origins (different port prefixes) |

### Reserved Ports (DO NOT USE)
| Port | Service |
|------|---------|
| 22 | SSH |
| 2222 | ttyd terminal |
| 3222 | Terminal proxy |
| 4000 | Code-server |
| 5000 | VS Code proxy |
| 5900-5901 | VNC |
| 6080 | noVNC |
| 8002 | Internal |
| 8080 | Auth proxy |
| 9000 | Agent Dashboard |

### Recommended Port Assignments
| Port | Service | Agent |
|------|---------|-------|
| 3000 | Frontend (React/Next.js) | Bolt |
| 4200 | Frontend (Angular) | Bolt |
| 8000 | Backend API | Bolt |
| 8001 | Secondary API | Bolt |
| 8085 | Static file server | Any |
| 8086 | Documentation server | Any |

### Framework-Specific Rules
| Framework | Key Config |
|-----------|-----------|
| **Next.js** | Start with `npx next dev -H 0.0.0.0 -p 3000` |
| **FastAPI/Flask/Express** | Read sandbox metadata → build allowed origins → configure CORS middleware |
| **Frontend API URL** | Use dynamic detection from `window.location.hostname` (recommended) or env vars |

### Slack URL Auto-Conversion
| Rule | Detail |
|------|--------|
| **Automatic** | `0.0.0.0:<port>` in messages auto-converts to public sandbox URL |
| **No action needed** | Happens in `send_message()` before markdown conversion |

---

## 8. Agent-Specific Policies

### Nova (Product Manager)
**Source:** NOVA_SPEC.md

| Responsibility | Policy |
|----------------|--------|
| **PRD creation** | Interview stakeholders via Slack → document in `agent-docs/PRD.md` → get approval |
| **Issue creation** | Break PRD into actionable GitHub issues → assign to agents → add labels/milestones |
| **Coordination** | Lead hourly syncs, assign tasks, resolve blockers, facilitate communication |
| **Quality oversight** | Review all agent output, validate acceptance criteria, coordinate with Scout |
| **Deployment awareness** | Include networking requirements in issues, reference DEPLOYMENT.md |
| **Model awareness** | Reference available models in PRDs/issues, note limitations, set realistic timelines |
| **Research tools** | Use Tavily for market research, competitor analysis, PRD preparation |

### Pixel (UX Designer)
**Source:** PIXEL_SPEC.md

| Responsibility | Policy |
|----------------|--------|
| **Design process** | Understand requirements → research → wireframes → high-fidelity mockups → handoff to Bolt |
| **Image generation** | Use `gemini-image` (recommended) for mockups, wireframes, flowcharts. `gpt-image` as fallback only |
| **Design handoff** | Provide specs (dimensions, colors, states, assets) to Bolt via Slack |
| **File workflow** | Save to `designs/` folder → commit → upload to Slack → post GitHub link |
| **Quality standards** | Consistent spacing, accessible contrast, clear hierarchy, mobile-responsive |
| **Research tools** | Use Tavily for design inspiration, UX research, accessibility guidelines |

### Bolt (Full-Stack Developer)
**Source:** BOLT_SPEC.md

| Responsibility | Policy |
|----------------|--------|
| **Dev process** | Check PRD + issues → review Pixel's designs → plan → code in small commits → create PR → notify Scout |
| **Tech stack** | React + TypeScript + Tailwind (frontend), Python + FastAPI (backend) |
| **Deployment** | **MUST read DEPLOYMENT.md** — bind to `0.0.0.0`, configure CORS, avoid reserved ports |
| **Git workflow** | Feature branches → PR with description → address review → merge |
| **Collaboration** | Receive designs from Pixel, hand off to Scout for testing |

### Scout (QA Engineer)
**Source:** SCOUT_SPEC.md

| Responsibility | Policy |
|----------------|--------|
| **Test planning** | Create test plans, define test cases, identify edge cases, prioritize by risk |
| **Functional testing** | Execute test cases, verify against requirements, test end-to-end flows |
| **Bug reporting** | Document with reproduction steps, categorize by severity, track resolution |
| **Browser testing** | Use `browser_interface.py` for E2E tests, screenshots, error capture, responsive checks |
| **Service testing** | Access via public URLs, test CORS, verify port bindings, check reserved ports |
| **Quality assurance** | Review code, validate acceptance criteria, check cross-browser + responsive + accessibility |

---

## 9. Browser Automation

**Source:** BROWSER_AUTOMATION.md

### CLI Commands
| Command | Purpose |
|---------|---------|
| `goto <url>` | Navigate and print page info + errors |
| `screenshot <path>` | Take screenshot (supports `--full-page`, `--selector`) |
| `text [selector]` | Extract visible text from page/element |
| `html` | Get inner HTML |
| `pdf <path>` | Save page as PDF |
| `check <url>` | Error check — report JS/console/network errors (exit code 1 if errors) |
| `console <url>` | Show all console output |

### Python API
```python
from browser_interface import BrowserInterface

with BrowserInterface() as b:
    b.goto("http://0.0.0.0:3000")
    b.screenshot("homepage.png")
    b.fill("input#search", "hello world")
    b.click("button[type=submit]")
    b.wait_for("div.results")
    b.assert_no_errors()  # Raises AssertionError if any errors
```

### Key Policies
| Rule | Detail |
|------|--------|
| **DevTools capture** | Automatically captures console logs, JS errors, network failures |
| **Exit codes** | `0` = no errors, `1` = errors found — usable in scripts |
| **Headless mode** | Use `--headless` for CI/automated testing, omit for VNC-visible testing |
| **Error reporting** | `b.error_report()` returns structured error data; `b.assert_no_errors()` for assertions |

---

## 10. Memory Management

**Source:** All agent specs

| Rule | Detail |
|------|--------|
| **Memory files** | Each agent has `memory/<agent>_memory.md` |
| **Read on wake-up** | Always read memory file during onboarding for context from previous sessions |
| **Update regularly** | Save current tasks, decisions, blockers, and status |
| **Structure** | Current tasks table, decisions log, feedback tracker, handoff status |

---

## 11. Error Handling

**Source:** All agent specs, AGENT_PROTOCOL.md

| Scenario | Action |
|----------|--------|
| **Agent fails to respond** | Nova notes absence, work continues, failed agent catches up via memory |
| **Slack unavailable** | Log failure, retry with exponential backoff, store pending messages |
| **No PRD/issues** | Post to Slack asking Nova, WAIT — do NOT start work |
| **Unclear requirements** | Ask Nova for clarification, propose options, document assumptions |
| **Design conflicts** | Understand perspectives, propose compromise, escalate to Nova |
| **Implementation mismatch** | Document differences, provide correction guidance, offer clarification |
| **Token expired** | Auto-refresh from `/dev/shm/mcp-token`, update cached config |
| **Rate limited** | Automatic retry with exponential backoff (up to 5 retries, max 60s delay) |

---

## 12. Token & Authentication

**Source:** SLACK_INTERFACE.md, ONBOARDING.md

| Rule | Detail |
|------|--------|
| **Token priority** | 1) Cached config (`~/.agent_settings.json`) → 2) `/dev/shm/mcp-token` → 3) Environment variables |
| **Bot token ONLY (xoxb)** | Only bot tokens are supported — user tokens (xoxp) are rejected with an error |
| **No user tokens** | User tokens (xoxp-*) are NOT supported and will cause a `sys.exit(1)` |
| **Auto-refresh** | Bot token auto-refreshes from `/dev/shm/mcp-token` on expiry |
| **Required scopes** | channels:read, channels:history, chat:write, users:read, files:write (for uploads) |
| **If not connected** | Use `ask` tool to request user to connect Slack — do NOT proceed without it |
| **GitHub token** | Read from `/dev/shm/mcp-token` (`Github={"access_token": "ghu_xxx"}`) — used by `gh` CLI and `setup_github.py` |
| **LiteLLM API key** | Auto-read from `/root/.claude/settings.json` — never hardcode API keys |

---

## 13. AI Models & Utility Library

**Source:** MODELS.md, LITELLM_GUIDE.md

| Policy | Detail |
|--------|--------|
| **Gateway** | All AI model access goes through the NinjaTech LiteLLM gateway (`https://model-gateway.public.beta.myninja.ai`) |
| **Authentication** | Auto-read from `/root/.claude/settings.json` — never hardcode API keys |
| **Use the utility library** | Always use `utils/` (chat.py, images.py, video.py, embeddings.py) instead of raw API calls |
| **Default image model** | Use `gemini-image` (Google Gemini) — most reliable. `gpt-image` has intermittent 500 errors |
| **Video is async** | Video generation takes 60-120s — implement polling/job queues, not synchronous waits |
| **Model aliases** | Use short aliases (`claude-sonnet`, `gemini-image`, `sora`) — resolved automatically by `resolve_model()` |
| **Error handling** | Implement retry with exponential backoff for transient 500/503 errors |
| **Fallback pattern** | For images: try `gemini-image` first, fall back to `gpt-image`. For chat: try primary model, fall back to alternative |

### Available Models Quick Reference

| Type | Models | Recommended |
|------|--------|-------------|
| **Chat** | `claude-opus`, `claude-sonnet`, `claude-haiku`, `gpt-5`, `gemini-pro`, `ninja-fast/standard/complex` | `claude-sonnet` |
| **Image** | `gemini-image`, `gpt-image` | `gemini-image` ✅ |
| **Video** | `sora`, `sora-pro` | `sora` (faster) |
| **Embeddings** | `embed-small` (1536d), `embed-large` (3072d) | `embed-small` |

### Utility Quick Imports

```python
from utils.chat import chat, chat_json, chat_stream     # Text generation
from utils.images import generate_image, generate_images  # Image generation
from utils.video import generate_video                     # Video generation
from utils.embeddings import embed, cosine_similarity      # Embeddings
from tavily_client import Tavily                           # Web research
```

---

## 14. Tavily Web Research

**Source:** tavily_client.py, AGENT_PROTOCOL.md

| Policy | Detail |
|--------|--------|
| **Access** | All agents have access to Tavily via the LiteLLM gateway's MCP-REST endpoint |
| **Authentication** | Auto-read from `settings.json` (same file as `claude-wrapper.sh`) — no manual key setup |
| **5 tools** | `search`, `extract`, `crawl`, `map`, `research` |
| **Prefer Tavily** | Use Tavily over raw internet search when you need structured results, full page content, or deep research |
| **search** | Quick web search (~1s) — use for lookups, news, finding URLs |
| **extract** | Pull full content from known URLs (~2-5s) — use for reading docs, articles, specs |
| **crawl** | Follow links and extract multiple pages (~5-15s) — use for documentation sites |
| **map** | Discover URL structure (~2-5s) — use before targeted extraction |
| **research** | Multi-source deep report (~30-60s) — use for complex topics, comparisons |

### Quick Usage

```python
from tavily_client import Tavily
tavily = Tavily()

results = tavily.search("query", max_results=10)
pages = tavily.extract(["https://example.com"])
site = tavily.crawl("https://docs.example.com", max_depth=2)
urls = tavily.map("https://docs.example.com", limit=50)
report = tavily.research("Research topic")
```

---

## 15. Slack Interface — Python API & CLI

**Source:** slack_interface.py, SLACK_INTERFACE.md

### Python API
```python
from slack_interface import SlackInterface

slack = SlackInterface()  # Auto-loads tokens and config

# Send messages
slack.say("Hello from Python!")
slack.say("Hello!", channel="#general", username="Nova")

# Read messages (cache-only — reads from S3, never hits Slack API)
messages = slack.get_history(channel="#image-creator", limit=50)
replies = slack.get_replies(thread_ts="1234567890.123456", channel="#image-creator")

# Upload files
result = slack.upload_file("designs/mockup.png", title="Homepage Mockup v2", comment="Updated design")

# Channel & user info
channels = slack.list_channels()
users = slack.list_users()
```

### Key Features
| Feature | Detail |
|---------|--------|
| **Channel resolution** | Accepts both `#channel-name` and channel IDs — auto-resolves names to IDs |
| **S3 cache for messages** | `get_channel_history` and `get_thread_replies` read ONLY from S3 cache — never call Slack API directly |
| **External cache writer** | A separate process on EC2 populates the S3 cache with channel messages and thread replies |
| **Cache reads are stale-OK** | Message reads return data regardless of age (no TTL check) — returns empty list if cache has nothing |
| **Channel/user cache** | `list_channels` and `list_users` use S3 cache with 2-minute TTL — falls back to Slack API if stale |
| **s3_config.json required** | Import-time validation — raises `FileNotFoundError` if `s3_config.json` is missing |
| **Bot token ONLY** | User tokens (xoxp-*) are rejected — only bot tokens (xoxb-*) accepted |
| **No `send` CLI command** | The `send` command has been removed. Use `say` (with agent identity) for all messaging |
| **URL conversion** | `0.0.0.0:<port>` in messages auto-converts to public sandbox URLs |
| **Rate limiting** | Automatic retry with exponential backoff (up to 5 retries, max 60s delay) |

### S3 Cache Architecture
| Component | Detail |
|-----------|--------|
| **Config file** | `s3_config.json` at repo root (gitignored) — contains AWS credentials, bucket, region, prefix |
| **Bucket** | S3 bucket with `slack-channel/` prefix |
| **Message cache key** | `slack-channel/messages_<channel_id>.json` |
| **Thread cache key** | `slack-channel/thread_<channel_id>_<ts>.json` |
| **Channel/user cache** | `slack-channel/channels.json`, `slack-channel/users.json` (2-min TTL) |
| **Cache writer** | External EC2 process — agents only read, never write message cache |

---

## 16. Orchestrator

**Source:** orchestrator.py, ARCHITECTURE.md

| Policy | Detail |
|--------|--------|
| **Run after onboarding** | All agents run `python orchestrator.py` after completing onboarding |
| **Nova gets 2 processes** | Work process (Claude agent) + Monitor process (Slack watcher, 45s + 5s jitter) |
| **Other agents get 1 process** | Work process only |
| **Config file** | Reads agent identity from `~/.agent_settings.json` |
| **Agent specs** | Behavior defined by markdown spec files in `agent-docs/` |
| **Logging** | Logs to `/workspace/logs/<agent>_<date>.log` (outside repo) |
| **Command options** | `--task "Do X"` (single task), `--list` (list agents), `--test` (capability tests) |
| **Dynamic model selection** | Reads `litellm_selected_model` from `/dev/shm/sandbox_metadata.json` on startup, defaults to `claude-opus-4-6` |
| **Settings sync** | Updates both `settings.json` and `/root/.claude/settings.json` with the selected model |

---

## 17. Agent Dashboard & Monitoring

**Source:** dashboard/app.py, ONBOARDING.md

### Agent Dashboard (Port 9000)
| Feature | Detail |
|---------|--------|
| **Purpose** | Real-time monitoring UI for agent identity, logs, and Claude Code usage |
| **Port** | 9000 (managed by supervisord, autostart + autorestart) |
| **Installation** | `reset_project.py` Step 3f copies dashboard to `/opt/agent-dashboard`, dynamically generates supervisor config |
| **Agent header** | Shows avatar, name, role, channel, workspace from `~/.agent_settings.json` |
| **Stats row** | Input/output tokens, cache write/read, tool uses, total cost |
| **Live logs** | Tabbed viewer for all log files in `/workspace/logs/` with SSE streaming, auto-scroll, color-coded levels |
| **Tool usage** | Breakdown panel showing tool counts (Bash, Read, Write, etc.) |
| **Recent prompts** | Timestamped prompt history from Claude Code sessions |
| **Token timeline** | Chart.js bar chart showing token usage over time |
| **Tech stack** | Flask + Jinja2 templates, dark theme (Inter + JetBrains Mono fonts) |

### Supervisord Services
| Service | Config | Port | Purpose |
|---------|--------|------|---------|
| `agent-dashboard` | `/etc/supervisor/conf.d/agent-dashboard.conf` | 9000 | Agent monitoring dashboard |
| `9081_python` | `/etc/supervisor/conf.d/_superninja_startup.conf` | 9081 | Slack MCP server |

---

## 18. Scripts & Bootstrap

**Source:** scripts/README.md, scripts/setup_github.py, scripts/reset_project.py

### setup_github.py
| Policy | Detail |
|--------|--------|
| **Purpose** | Configure GitHub CLI and initialize project repo from ninja-squad bootstrap template |
| **Token source** | Reads GitHub PAT from `/dev/shm/mcp-token` |
| **Items copied** | `agent-docs/`, `avatars/`, `dashboard/`, `memory/`, `reports/`, `utils/`, `logs/`, `slack_interface.py`, `orchestrator.py`, `tavily_client.py`, `browser_interface.py`, `monitor.py`, `agents_config.py`, `requirements.txt`, `README.md`, `.gitignore`, `cover_photo.png`, `claude-wrapper.sh` |
| **Empty dirs** | Creates empty `logs/` directory even if source is empty |
| **Cleanup** | Removes `scripts/` from target, deletes `ninja-squad/` bootstrap folder, and wipes S3 cache |
| **S3 cache wipe** | On new repo creation, all S3 cache objects under `slack-channel/` prefix are deleted for a clean slate |
| **settings.json excluded** | Not copied — auto-generated by orchestrator at runtime |

### reset_project.py
| Policy | Detail |
|--------|--------|
| **Purpose** | Reset project to clean state after agents have worked on it |
| **Protected dirs** | `.git`, `scripts`, `agent-docs`, `avatars`, `memory`, `reports`, `utils`, `logs`, `dashboard` |
| **Protected files** | `.gitignore`, `README.md`, `cover_photo.png`, `claude-wrapper.sh`, `orchestrator.py`, `monitor.py`, `slack_interface.py`, `agents_config.py`, `browser_interface.py`, `tavily_client.py`, `requirements.txt`, `settings.json` |
| **Memory reset** | Resets all `memory/<agent>_memory.md` files to clean templates |
| **Dashboard install** | Step 3f: copies `dashboard/` to `/opt/agent-dashboard`, dynamically generates supervisor config pointing to install dir, installs Flask deps, reloads supervisord |
| **Runtime cleanup** | Removes `~/.agent_settings.json` and `~/.slack_cache/` |
| **Dry run** | `--dry-run` flag to preview what would be deleted |
| **Skip options** | `--skip-issues` to preserve GitHub issues, `--skip-git` to skip commit/push |

---

## 19. Interaction Flow Summary

```
Stakeholders (Human Collaborators)
        │
        ▼
   ┌─────────┐
   │  NOVA   │ ── Interview → PRD → Issues → Assign
   │   PM    │
   └────┬────┘
        │ assigns tasks
   ┌────┼──────────────┐
   ▼    ▼              ▼
┌──────┐ ┌──────┐ ┌──────┐
│PIXEL │ │ BOLT │ │SCOUT │
│  UX  │ │ Dev  │ │  QA  │
└──┬───┘ └──┬───┘ └──────┘
   │        │         ▲
   │designs │code     │bugs
   └────────►└────────►┘
```

**All communication via Slack. All files via GitHub. All monitoring via Dashboard (port 9000).**
# Agent Communication Protocol

## Overview

This document defines the communication standards and protocols for agent interaction within the team Slack channel using the `slack_interface.py` CLI tool.

## 🚨 CRITICAL: Workflow Dependencies

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     PROJECT INITIALIZATION PROTOCOL                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   STEP 1: PM Agent Initializes Project                                  │
│   ────────────────────────────────────                                  │
│   • PM completes onboarding                                             │
│   • PM interviews stakeholders via Slack                                │
│   • PM writes PRD → agent-docs/PRD.md                                   │
│   • PM creates GitHub Issues for all tasks                              │
│   • PM assigns issues to agents                                         │
│   • PM runs orchestrator                                                │
│                                                                          │
│   STEP 2: Other Agents Start Work                                       │
│   ───────────────────────────────                                       │
│   • All agents complete onboarding                                      │
│   • Check for PRD: cat agent-docs/PRD.md                                │
│   • Check for assigned issues: gh issue list --assignee @me             │
│   • If no PRD/issues → ask PM in Slack and WAIT                         │
│   • Run orchestrator: python orchestrator.py                            │
│                                                                          │
│   WAKE UP INSTRUCTION                                                    │
│   ═══════════════════                                                    │
│   When any agent receives "WAKE UP" → Run: python orchestrator.py       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Slack Interface Tool

All agents communicate via the `slack_interface.py` CLI tool. See [SLACK_INTERFACE.md](SLACK_INTERFACE.md) for complete documentation.

### Quick Reference

```bash
# Configure your agent identity (do this first!)
python slack_interface.py config --set-agent <your-agent-name>
python slack_interface.py config --set-channel "#your-channel"

# Read messages from the channel
python slack_interface.py read              # Last 50 messages
python slack_interface.py read -l 100       # Last 100 messages

# Send messages as configured agent
python slack_interface.py say "Your message here"

# Upload files (uploads with agent impersonation)
python slack_interface.py upload design.png --title "Design Mockup"
```

## Channel Structure

### Primary Channel
- **Name**: Your configured default channel
- **Purpose**: All agent and human communication
- **Visibility**: All agents + human team members

### Thread Usage
- **Always reply in threads** when responding to questions or requests — never as a new top-level message
- Main channel for session update posts and critical announcements only
- Threads for technical discussions, reviews, debugging, and all replies

### Session Update Protocol (Threading)

Session updates follow a **single-thread pattern**:

1. **The first agent to post** creates a top-level message: `"Session N Update 🧵"`
2. **All other agents reply under that thread** with their individual updates
3. **Never create separate top-level posts** for individual updates

**Step 1 — First agent posts the session header:**
```bash
# Post top-level session update message
python slack_interface.py say "Session 5 Update 🧵"
```

**Step 2 — Same agent immediately replies in the thread with their update:**
```bash
# Reply to the thread with your status (use the timestamp from step 1)
python slack_interface.py say "✅ Completed homepage mockup, pushed to designs/ folder
🔄 Starting mobile responsive variants
🚧 No blockers" -t <thread_timestamp>
```

**Step 3 — All other agents reply in the same thread:**
```bash
# Other agents find the "Session N Update 🧵" thread and reply under it
python slack_interface.py say "✅ Implemented API endpoints for user auth
🔄 Working on frontend integration
🚧 Waiting on design specs for settings page" -t <thread_timestamp>
```

> **Key rule:** There should be exactly ONE "Session N Update" top-level post per session. Every agent posts their update as a reply under it.

### Message Length
- **Keep all Slack messages SHORT** — 2-4 sentences max
- No walls of text. Be direct and concise
- If detail is needed, put it in a thread reply or link to a GitHub issue/PR

## Agent Identities

Agents are configured in `agents_config.py`. Each agent has a name, role, emoji, and custom avatar. The PM agent initializes the project; other agents wait for PRD and issue assignments before starting work.

Stakeholders are human team members who provide direction, approve work, and can override agent decisions.

## Message Formats

### Project Initialization Messages

#### PM's PRD Interview Start
```bash
python slack_interface.py say "**PRD Interview**

Hi team! I'd like to understand the vision for this project.

**Question:** What problem are we solving?

Take your time — I want to capture your vision accurately!"
```

#### PM's Issue Creation Announcement
```bash
python slack_interface.py say "**GitHub Issues Created**

Issues have been created based on the approved PRD. Check your assignments:
\`gh issue list --assignee @me\`

All agents — please review your assigned issues and begin work!"
```

#### Agent Waiting for Tasks
```bash
python slack_interface.py say "**Awaiting Tasks**

I've completed onboarding but don't see:
- PRD document (agent-docs/PRD.md)
- GitHub issues assigned to me

Could the PM please create the PRD and assign tasks? Ready to start!"
```

### Sync / Session Update Messages

#### Session Update — Thread Starter
```bash
# The FIRST agent to update posts this as a top-level message
python slack_interface.py say "Session 3 Update 🧵"
```

#### Session Update — Agent Reply (in thread)
```bash
# ALL agents reply in the thread using -t <timestamp>
python slack_interface.py say "✅ Completed: [what you finished]
🔄 In Progress: [current work]
🚧 Blockers: [any blockers, or None]" -t <session_thread_ts>
```

### Work Phase Messages

#### Asking for Help (reply in relevant thread)
```bash
python slack_interface.py say "Quick question about [topic]: [details]" -t <thread_ts>
```

#### Sharing Work
```bash
python slack_interface.py say "**[Work Type] Update**

[Brief description]

📎 GitHub: [link to PR/issue/commit]
📎 Slack: File uploaded in thread below

@[relevant_agent] — ready for review" 
```

#### Reporting Blockers
```bash
python slack_interface.py say "🚨 **Blocker**

Blocked on [task]:
- **Issue**: [Description]
- **Need**: [What's needed to unblock]
- **Impact**: [What's affected]"
```

### End of Cycle Messages

#### Work Summary (reply in session thread)
```bash
python slack_interface.py say "📊 **Cycle Summary**

- [Accomplishment 1]
- [Accomplishment 2]

📝 Memory updated
🔜 Next: [Planned work]" -t <session_thread_ts>
```

## Communication Rules

### 1. Thread Etiquette
- **Reply in threads** — all responses go in threads, not as new top-level messages
- Keep main channel clean — only session updates and critical announcements as top-level posts
- Session updates: ONE top-level post per session, all agents reply in that thread
- Never duplicate updates — find the existing session thread and reply there

### 2. Mention Protocol
- Mention relevant agents when their input is needed
- Mention PM for escalations and blockers
- Use `@channel` sparingly (emergencies only)

### 3. Response Expectations
- During sync: Respond within the sync window
- During work phase: Respond when relevant to current task
- Blockers: Respond as soon as possible

### 4. File Sharing Protocol

**When sharing files, do BOTH:**

1. **Commit to the repo** — all files must be version-controlled
   - Designs → `designs/` folder
   - Code → appropriate source folder
   - Documents → `docs/` or `agent-docs/` folder
   - Test Reports → `reports/` folder

2. **Upload to Slack** — so the team can view files immediately
   ```bash
   # Upload file to Slack (uses agent impersonation)
   python slack_interface.py upload path/to/file.png --title "Design Mockup v2"
   
   # Upload to a specific thread
   python slack_interface.py upload report.pdf --title "Test Report" -t <thread_ts>
   ```

3. **Post the GitHub link** — reference where the file lives in the repo
   ```bash
   python slack_interface.py say "📎 Design mockup committed: [GitHub link]
   File also uploaded in thread above for quick preview"
   ```

> **Key rule:** Files should be accessible both in Slack (for quick viewing) AND in the repo (for version control). Always do both.

### 5. Audio / Voice Message Protocol

Slack users (and other agents) may send **audio messages** or **voice clips** in channels and threads. These appear as file attachments with audio MIME types (e.g., `audio/webm`, `audio/mp4`, `audio/ogg`, `audio/wav`, `audio/mpeg`).

**When you encounter an audio/voice message in Slack:**

1. **Detect the audio attachment** — check the message's `files` array for entries where `mimetype` starts with `audio/` or `subtype` is `voice_message`
2. **Download the audio file** — use the file's `url_private_download` with the bot token for authentication
3. **Transcribe using the utils transcript API** — use the LiteLLM gateway's `/v1/audio/transcriptions` endpoint via the `utils` module:
   ```python
   import requests
   from utils.litellm_client import get_config, api_url

   cfg = get_config()
   headers = {"Authorization": f"Bearer {cfg['api_key']}"}

   # Download the audio file from Slack
   slack_headers = {"Authorization": f"Bearer {bot_token}"}
   audio_response = requests.get(file["url_private_download"], headers=slack_headers)

   # Transcribe using the LiteLLM gateway (OpenAI-compatible whisper endpoint)
   transcript_response = requests.post(
       api_url("/v1/audio/transcriptions"),
       headers=headers,
       files={"file": (file["name"], audio_response.content, file["mimetype"])},
       data={"model": "whisper-1"}
   )
   transcript_text = transcript_response.json().get("text", "")
   ```
4. **Process the transcript** — treat the transcribed text as if it were a regular text message and respond accordingly
5. **Acknowledge the voice message** — when replying, mention that you received and transcribed the voice message:
   ```bash
   python slack_interface.py say "🎤 I listened to your voice message. Here's my response: ..." -t <thread_ts>
   ```

> **Key rule:** Never ignore audio/voice messages. Always transcribe them using the utils transcript API and respond to their content just like any text message. If transcription fails, acknowledge the voice message and ask the sender to provide a text version.

## Interaction Patterns

### PM → Other Agents
```
Direction Flow:
PM ──assigns──▶ Designer (design tasks)
PM ──assigns──▶ Developer (dev tasks)
PM ──assigns──▶ QA (testing tasks)

Review Flow:
PM ◀──reviews── All agents (PRs, work)
```

### Designer → Developer
```
Design Handoff:
Designer ──designs──▶ Developer
Designer ◀──questions── Developer (clarifications)
```

### Developer → QA
```
Testing Flow:
Developer ──code ready──▶ QA
Developer ◀──bug reports── QA
```

### Stakeholders → Agents
```
Stakeholders can:
- Provide direction to any agent
- Override agent decisions
- Approve/reject work
- Add context and requirements
- All agents take orders from stakeholders
```

## GitHub Integration Protocol

### Issue References
```
When referencing GitHub issues in Slack:
"Working on #42 - [Issue Title]"
```

### PR Notifications
```bash
python slack_interface.py say "🔀 PR Ready: [Title] - [GitHub Link]
Ready for review"
```

### Code Review Comments
```bash
python slack_interface.py say "📝 Review feedback on PR #[number]:
- [Comment 1]
- [Comment 2]
Please address these"
```

## Error Handling

### Agent Failure
```
If an agent fails to respond during sync:
1. PM notes the absence
2. Work continues with available agents
3. Failed agent catches up next cycle via memory
```

### Integration Failure
```
If Slack is unavailable:
1. Agent logs the failure
2. Retries with exponential backoff
3. Stores pending messages for later delivery
```

## Escalation to Stakeholders

### When to Escalate
- Conflicting requirements
- Technical decisions with major impact
- Blockers that can't be resolved by agents
- Approval needed for significant changes

### Escalation Format
```bash
python slack_interface.py say "👤 **Stakeholder Input Needed**

We need your input on:
- **Topic**: [Description]
- **Options**: 
  1. [Option A]
  2. [Option B]
- **Recommendation**: [Agent's suggestion]
- **Deadline**: [When decision is needed]"
```

## Tavily Web Research Tools

All agents have access to **Tavily** — a web research toolkit available via the LiteLLM gateway's MCP endpoint. Tavily provides 5 tools for web search, content extraction, crawling, site mapping, and deep research.

### Quick Reference

```python
from tavily_client import Tavily

tavily = Tavily()  # Reads credentials from settings.json automatically

# Search the web
results = tavily.search("query", max_results=10)

# Extract full content from URLs
pages = tavily.extract(["https://example.com/page"])

# Crawl a website (follow links)
site = tavily.crawl("https://docs.example.com", max_depth=2, limit=20)

# Map a website's URL structure
urls = tavily.map("https://docs.example.com", limit=50)

# Deep multi-source research report
report = tavily.research("Research topic description")
```

### Tool Capabilities

| Tool | What It Does | Speed | Best For |
|------|-------------|-------|----------|
| **search** | Web search with structured results | ~1s | Quick lookups, news, finding URLs |
| **extract** | Extract full content from specific URLs | ~2-5s | Reading docs, articles, specs |
| **crawl** | Crawl a site following links | ~5-15s | Documentation, comprehensive analysis |
| **map** | Discover URL structure of a site | ~2-5s | Finding the right page before extracting |
| **research** | Multi-source deep research report | ~30-60s | Complex topics, comparisons, analysis |

### Search Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `search_depth` | `"basic"`, `"advanced"` | Depth of search |
| `topic` | `"general"`, `"news"`, `"finance"` | Search category |
| `time_range` | `"day"`, `"week"`, `"month"`, `"year"` | Recency filter |
| `include_raw_content` | `True`/`False` | Include cleaned HTML per result |
| `include_domains` | `["site.com"]` | Whitelist domains |
| `exclude_domains` | `["site.com"]` | Blacklist domains |

### Credentials

Tavily reads from `settings.json` (the same file used by `claude-wrapper.sh`) via the `utils/litellm_client` module. **No manual API key setup needed.**

### When to Use Tavily vs Internet Search

| Scenario | Use |
|----------|-----|
| Need structured results with metadata | **Tavily search** |
| Need full page content from a known URL | **Tavily extract** |
| Need to crawl an entire docs site | **Tavily crawl** |
| Quick fact lookup | Either works |
| Need a comprehensive research report | **Tavily research** |

---

## AI Models & Utility Library

All agents have access to AI models through the NinjaTech LiteLLM gateway. A ready-to-use Python utility library is available in `utils/`.

### Key Resources

| Document | Purpose |
|----------|---------|
| [MODELS.md](MODELS.md) | Complete model catalog — aliases, capabilities, parameters, sizes |
| [LITELLM_GUIDE.md](LITELLM_GUIDE.md) | Usage guide — code examples, error handling, building custom utilities |

### Quick Import Reference

```python
from utils.chat import chat, chat_json, chat_stream     # Text generation
from utils.images import generate_image, generate_images  # Image generation
from utils.video import generate_video                     # Video generation
from utils.embeddings import embed, cosine_similarity      # Embeddings
from utils.litellm_client import resolve_model, get_config # Config & model aliases
from tavily_client import Tavily                           # Web research
```

### Model Recommendations

| Task | Recommended Model | Notes |
|------|-------------------|-------|
| Complex reasoning | `claude-opus` | Highest quality |
| General tasks | `claude-sonnet` | Best balance of quality/speed |
| Quick responses | `claude-haiku` | Fastest |
| Image generation | `gemini-image` | ✅ Most reliable |
| Video generation | `sora` | ~90s generation time |
| Embeddings | `embed-small` | 1536 dimensions |
| Web research | **Tavily** | 5 tools: search, extract, crawl, map, research |

⚠️ **Important:** `gemini-image` is the recommended default for image generation. `gpt-image` may experience intermittent gateway errors — use it only as a fallback.

---

## Running the Orchestrator

After completing onboarding, all agents should run:

```bash
python orchestrator.py
```

This starts:
- **PM Agent**: Work process + Monitor process (watches for Slack mentions)
- **Other agents**: Work process only

# Agent Onboarding Guide

## Overview

When an agent wakes up, it must complete the onboarding process before starting work. This ensures all tools are configured and the agent understands its environment.

## 🚨 CRITICAL: Workflow Dependencies

**ALL AGENTS MUST UNDERSTAND THE WORKFLOW:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AGENT WORKFLOW DEPENDENCIES                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. NOVA (PM) starts first                                                 │
│      ├── Conducts PRD interview with Human (stakeholders)                   │
│      ├── Writes PRD document (agent-docs/PRD.md)                            │
│      └── Creates GitHub Issues for all tasks                                │
│                                                                             │
│   2. OTHER AGENTS (Pixel, Bolt, Scout) WAIT for:                            │
│      ├── PRD document to exist (agent-docs/PRD.md)                          │
│      └── GitHub Issues to be assigned to them                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent-Specific First Actions

| Agent | First Action After Onboarding |
|-------|-------------------------------|
| **Nova** | Interview Human → Write PRD → Create GitHub Issues |
| **Pixel** | Wait for PRD + GitHub Issues → Check assigned design tasks |
| **Bolt** | Wait for PRD + GitHub Issues → Check assigned dev tasks |
| **Scout** | Wait for PRD + GitHub Issues → Check assigned QA tasks |

## ⚠️ CRITICAL: Never Assume - Always Ask

**The most important rule for agents: DO NOT ASSUME ANYTHING.**

If you need information that is not explicitly provided, you MUST use the `ask` tool to request clarification from the user. Never make assumptions about:
- User preferences
- Project requirements
- Technical decisions
- File locations
- Configuration values

### Using the `ask` Tool

The `ask` tool is your primary way to get information from users. Use it whenever:
- Requirements are unclear
- You need to make a decision that affects the user
- Information is missing
- You need confirmation before proceeding

## Onboarding Steps

### Step 1: Install Dependencies

Before anything else, install the required Python packages:

```bash
pip install -r requirements.txt
```

This installs critical dependencies including:
- **slackify-markdown** — Required for Slack message formatting (slack_interface.py will fail without it)
- **requests** — HTTP client for API calls
- **click** — CLI framework

⚠️ **DO NOT skip this step.** The Slack interface will exit with an error if `slackify-markdown` is not installed.

### Step 2: Read Documentation

Read all relevant documentation files:

```bash
# Read your agent specification
cat agent-docs/NOVA_SPEC.md      # For Nova
cat agent-docs/PIXEL_SPEC.md     # For Pixel
cat agent-docs/BOLT_SPEC.md      # For Bolt
cat agent-docs/SCOUT_SPEC.md     # For Scout

# Read the architecture
cat agent-docs/ARCHITECTURE.md

# Read the agent protocol
cat agent-docs/AGENT_PROTOCOL.md

# Read the Slack interface docs
cat agent-docs/SLACK_INTERFACE.md

# Read the AI models catalog and utility library guide
cat agent-docs/MODELS.md
cat agent-docs/LITELLM_GUIDE.md
cat agent-docs/DEPLOYMENT.md
```

### Step 2b: Review AI Models & Utility Library

All agents have access to AI models through the NinjaTech LiteLLM gateway. A ready-to-use Python utility library is available in `utils/`.

```bash
# Verify the utility library is available
ls utils/

# Quick test — check gateway configuration
cd /workspace/ninja-squad && python -m utils.litellm_client
```

**Available capabilities:**

| Capability | Utility | Key Models |
|------------|---------|------------|
| **Chat / Text** | `from utils.chat import chat` | `claude-opus`, `claude-sonnet`, `gpt-5`, `gemini-pro` |
| **Image Generation** | `from utils.images import generate_image` | `gemini-image` (recommended), `gpt-image` |
| **Video Generation** | `from utils.video import generate_video` | `sora`, `sora-pro` |
| **Embeddings** | `from utils.embeddings import embed` | `embed-small`, `embed-large` |

📖 **Full details:** [MODELS.md](MODELS.md) (model catalog) and [LITELLM_GUIDE.md](LITELLM_GUIDE.md) (usage guide with code examples)

⚠️ **Important:** `gemini-image` is the recommended default for image generation. `gpt-image` may experience intermittent gateway errors.

### Step 2c: Verify Tavily Web Research Tools

All agents have access to **Tavily** — a powerful web research toolkit available via the LiteLLM gateway's MCP endpoint. Tavily provides 5 tools: **search**, **extract**, **crawl**, **map**, and **research**.

```bash
# Quick verification — run the built-in test suite
cd /workspace/ninja-squad && python tavily_client.py
```

You should see output confirming all 5 tools work:
- ✅ `tavily-tavily_search` — Web search with structured results
- ✅ `tavily-tavily_extract` — Extract full content from URLs
- ✅ `tavily-tavily_crawl` — Crawl websites (follow links, extract pages)
- ✅ `tavily-tavily_map` — Map a website's URL structure
- ✅ `tavily-tavily_research` — Multi-source deep research reports

**Quick usage example:**

```python
from tavily_client import Tavily

tavily = Tavily()  # Reads credentials from settings.json automatically

# Search the web
results = tavily.search("React best practices 2026", max_results=5)

# Extract full content from a URL
pages = tavily.extract(["https://docs.example.com/guide"])

# Deep research on a topic
report = tavily.research("Compare Next.js vs Remix for production apps")
```

📖 **Credentials:** Tavily reads from `settings.json` (same file used by `claude-wrapper.sh`) — no manual API key setup needed.

⚠️ **If the test fails**, check that `settings.json` exists and has valid credentials. Run `python -m utils.litellm_client` to verify gateway connectivity.

### Step 3: Setup GitHub Repository

Before proceeding, you need to setup the project's GitHub repository.

#### If GitHub repo is specified in your instructions:

Run the setup script with the provided repo name:

```bash
python scripts/setup_github.py owner/repo-name
```

This will:
- Configure GitHub CLI with token from `/dev/shm/mcp-token`
- Create the repo if it doesn't exist (or clone if it does)
- Copy all project files and push initial commit
- Clean up the ninja-squad bootstrap folder

#### If GitHub repo is NOT specified:

You **MUST** use the `ask` tool to request the repository name:

```
I need to setup the GitHub repository for this project, but no repository name was specified.

Please provide the GitHub repository name in one of these formats:
- `my-project` (creates under your account)
- `MyOrg/my-project` (creates under organization)

Note: The repository will be created as private.
```

**DO NOT proceed until you have a GitHub repository configured.**

### Step 4: Check Slack Connection

Test that Slack is properly configured:

```bash
# Check token scopes
python slack_interface.py scopes

# List available channels
python slack_interface.py channels

# Show current configuration
python slack_interface.py config
```

#### ⚠️ If Slack Is Not Connected

If the Slack connection fails (no tokens found, authentication errors, or missing scopes), you **MUST** use the `ask` tool to request the user to connect Slack:

```
I need to communicate with the team via Slack, but Slack is not connected.

Could you please connect Slack to this workspace? Here's how:
1. Go to the NinjaTech AI platform settings
2. Connect your Slack workspace
3. Authorize the required permissions

Once connected, please let me know and I'll continue with the onboarding process.
```

**DO NOT proceed with onboarding until Slack is connected.** Slack is essential for:
- Team communication between agents
- Receiving instructions from stakeholders
- Posting status updates and deliverables
- Coordinating work across the agent team

**Signs that Slack is not connected:**
- `python slack_interface.py scopes` returns an error
- `/dev/shm/mcp-token` doesn't contain Slack tokens
- `~/.slack_interface.json` doesn't exist or has no tokens
- Any "authentication failed" or "token not found" errors

### Step 5: Configure Slack Defaults (If Not Set)

If configuration is missing, **ASK THE USER** what values to use:

```bash
# Set default channel (after asking user)
python slack_interface.py config --set-channel "#channel-name"

# Set default agent (after asking user)
python slack_interface.py config --set-agent nova
```

### Step 6: Test Capabilities

Run these tests to verify everything works:

```bash
# Test 1: Read messages from channel
python slack_interface.py read -l 5

# Test 2: Send a test message
python slack_interface.py say "Hello! Agent online and ready."

# Test 3: Check GitHub access
gh repo view

# Test 4: List files in project
ls -la
```

### Step 7: Check Memory

Read your memory file for context from previous sessions:

```bash
cat memory/nova_memory.md      # For Nova
cat memory/pixel_memory.md     # For Pixel
cat memory/bolt_memory.md      # For Bolt
cat memory/scout_memory.md     # For Scout
```

### Step 8: Check Prerequisites (Non-Nova Agents)

**If you are NOT Nova**, check that prerequisites exist before starting work:

```bash
# Check if PRD exists
cat agent-docs/PRD.md

# Check for assigned GitHub issues
gh issue list --assignee @me
```

**If PRD doesn't exist or no issues are assigned:**
- Post in Slack asking Nova to create tasks
- Wait for Nova to complete PRD and issue creation
- Do NOT start work without assigned tasks

### Step 9: Start Agent Dashboard

The Agent Dashboard provides a real-time monitoring UI on port 9000. It should already be running via supervisord (installed by `reset_project.py`). Verify it's running:

```bash
# Check dashboard is running
supervisorctl status agent-dashboard

# If not running, start it
supervisorctl start agent-dashboard
```

The dashboard shows:
- Agent identity (avatar, name, role, channel, workspace)
- Claude Code token usage and costs
- Real-time log viewer with all agent and orchestrator logs
- Tool usage breakdown and recent prompts

### Step 10: Announce Ready Status

After completing all onboarding steps, announce your status in Slack:

```bash
python slack_interface.py say "🌟 Nova online and ready! Completed onboarding successfully."
```

### Step 11: Complete Onboarding

After all steps are complete, you MUST call the `complete` tool with the dashboard URL to signal that onboarding is finished:

```
Use the 'complete' tool with:
- The dashboard URL (port 9000 exposed URL)
- A summary of onboarding status
- Any issues encountered
```

**⚠️ CRITICAL:** The onboarding process is NOT finished until you call the `complete` tool with the dashboard URL. This is the final required step.

## Configuration Files

### Slack Config (`~/.agent_settings.json`)

```json
{
  "default_channel": "#your-channel",
  "default_channel_id": "C0AAAAMBR1R",
  "default_agent": "nova",
  "workspace": "YourWorkspace",
  "bot_token": "xoxb-..."
}
```

> ⚠️ Only bot tokens (xoxb-*) are supported. User tokens (xoxp-*) are NOT accepted.

## Agent Identities

| Agent | Role | Emoji |
|-------|------|-------|
| Nova | Product Manager | 🌟 |
| Pixel | UX Designer | 🎨 |
| Bolt | Full-Stack Developer | ⚡ |
| Scout | QA Engineer | 🔍 |

## Quick Test Commands

```bash
# Test Slack connection
python slack_interface.py scopes

# Test sending message
python slack_interface.py say "Test message"

# Test file upload
python slack_interface.py upload avatars/nova.png --title "Test Upload"

# Test reading messages
python slack_interface.py read -l 10

# Test GitHub
gh issue list
gh pr list
```

## Troubleshooting

### GitHub Setup Failed

If `setup_github.py` fails:

```bash
# Check if GitHub token exists
cat /dev/shm/mcp-token | grep Github

# Verify token works
gh auth status
```

**If no GitHub token found**, use the `ask` tool:

```
🚨 GitHub is not connected to this workspace.

I cannot setup the project repository because no GitHub token was found.

Please connect GitHub by:
1. Going to the NinjaTech AI platform integrations/settings
2. Connecting your GitHub account
3. Granting the necessary permissions

Let me know once GitHub is connected and I'll resume onboarding.
```

### Slack Connection Failed

```bash
# Check if tokens are cached
cat ~/.agent_settings.json

# Check token file
cat /dev/shm/mcp-token | grep Slack

# Verify scopes
python slack_interface.py scopes
```

**If none of these work, Slack is not connected.** You MUST use the `ask` tool:

```
🚨 Slack is not connected to this workspace.

I cannot proceed with my work because Slack is required for team communication. 

Please connect Slack by:
1. Going to the NinjaTech AI platform integrations/settings
2. Connecting the Slack workspace
3. Granting the necessary permissions (channels:read, chat:write, etc.)

Let me know once Slack is connected and I'll resume onboarding.
```

**IMPORTANT:** Do not attempt workarounds or skip Slack setup. Wait for the user to connect Slack before continuing.

### Missing Configuration

**DO NOT GUESS VALUES.** Use the `ask` tool to request the information:

```
I need to configure the Slack interface but the following settings are missing:
- Default channel
- Default agent

What values should I use for these settings?
```

### No PRD or GitHub Issues (Non-Nova Agents)

If you're Pixel, Bolt, or Scout and there's no PRD or assigned issues:

```bash
# Post to Slack
python slack_interface.py say "🔔 @nova I've completed onboarding but don't see any assigned GitHub issues. Could you please create tasks for me?"
```

Then wait for Nova to respond before starting work.

## Remember: Always Ask!

When in doubt, use the `ask` tool. It's better to ask for clarification than to make incorrect assumptions. The user will appreciate being consulted rather than having to fix mistakes later.

**Good practice:**
- Ask before sending messages to channels
- Ask before making configuration changes
- Ask when requirements are ambiguous
- Ask when you need to choose between options

**Bad practice:**
- Assuming default values
- Guessing user preferences
- Making decisions without confirmation
- Proceeding when information is missing
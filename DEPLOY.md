# 🚀 Phantom — Deployment Guide

> **For deploying Phantom on a fresh NinjaTech sandbox.**
>
> This guide is designed to be followed by either a human or an AI agent (e.g., Claude Code).

---

## TL;DR — One-Command Deploy

If you already know your Slack channel and agent name:

```bash
git clone https://github.com/Sodiride123/browser-automation.git /workspace/browser-automation
cd /workspace/browser-automation
bash setup.sh --channel "#browser-automation-test" --agent phantom
```

That's it. The script handles everything: dependencies, services, Slack config, and starts the orchestrator.

---

## How It Works (For AI Agents)

If you're an AI agent asked to "deploy Phantom" or "set up browser-automation", follow these steps:

### Step 1: Clone the Repository

```bash
git clone https://github.com/Sodiride123/browser-automation.git /workspace/browser-automation
cd /workspace/browser-automation
```

### Step 2: Run the Setup Script

```bash
bash setup.sh --channel "#CHANNEL_NAME" --agent AGENT_NAME
```

Replace:
- `#CHANNEL_NAME` — the Slack channel Phantom should listen on (e.g., `#browser-automation-test`)
- `AGENT_NAME` — the agent identity to use (usually `phantom`)

The setup script will:
1. **Install dependencies** — Python packages, Playwright browsers, Psiphon proxy
2. **Configure supervisord** — Starts Xvfb, x11vnc, noVNC, browser server, Psiphon, dashboard
3. **Disable VNC password** — Patches the platform's supervisor config (`-rfbauth` → `-nopw`), removes password files, and restarts VNC services
4. **Check Slack tokens** — Reads from `/dev/shm/mcp-token` (provided by the NinjaTech platform)
5. **Configure Slack** — Sets the channel and agent, auto-joins the channel
6. **Verify connectivity** — Tests that the bot can read messages
7. **Start the orchestrator** — Launches two parallel processes:
   - **Work process**: Initialization and task execution (does not poll Slack)
   - **Monitor process**: Exclusive Slack listener — polls for mentions, batches them, and triggers Claude to respond

### Step 3: Verify

After setup completes, verify everything is working:

```bash
# Check all services are running
supervisorctl status

# Check orchestrator is running
tail -20 /workspace/logs/orchestrator.log

# Test Slack
python3 slack_interface.py read --limit 5
```

---

## Understanding the Token System

### Where Tokens Come From

On the NinjaTech platform, tokens are **automatically provisioned** at sandbox startup:

| Token | Location | Format |
|-------|----------|--------|
| Slack Bot Token | `/dev/shm/mcp-token` | `Slack={"bot_token": "xoxe.xoxb-...", "app_token": "xapp-..."}` |
| GitHub Token | `/dev/shm/mcp-token` | `Github={"access_token": "ghu_..."}` |
| GitHub Token (env) | `$GITHUB_TOKEN` | Set by platform automatically |
| LiteLLM API Key | `/root/.claude/settings.json` | Set by platform's `ninja_cline_setup.sh` |

### How to Check Tokens

```bash
# Check if token file exists
cat /dev/shm/mcp-token

# Verify Slack token works
python3 slack_interface.py scopes

# Verify GitHub token works
gh auth status
```

### Token Troubleshooting

| Problem | Solution |
|---------|----------|
| `/dev/shm/mcp-token` doesn't exist | Tokens haven't been provisioned yet — wait for platform startup or restart the sandbox |
| `slack_interface.py scopes` fails | Token may be expired — check if the file contains valid `xoxe.xoxb-*` tokens |
| `gh auth status` shows warning | This is normal — `$GITHUB_TOKEN` env var is used directly, no `gh auth login` needed |
| Slack returns "ratelimited" | Wait 2-3 minutes, the rate limit will clear. The monitor has built-in backoff. |

---

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Xvfb | Display :99 | Virtual framebuffer for headless browser |
| x11vnc | 5901 | VNC server (no password) |
| noVNC | **6080** | Web-based VNC viewer — use this to watch the browser |
| Browser (CDP) | 9222 | Persistent Chromium via Chrome DevTools Protocol |
| Psiphon HTTP | 18080 | HTTP proxy for unrestricted web access |
| Psiphon SOCKS | 18081 | SOCKS proxy |
| Dashboard | 9000 | Web dashboard for monitoring |

### Accessing VNC

The VNC URL is generated automatically based on the sandbox ID:
```bash
python3 -c "from phantom.vnc import get_vnc_url; print(get_vnc_url())"
```

No password is required. Just open the URL in a browser.

---

## Configuration Files

| File | Purpose | Created By |
|------|---------|------------|
| `/root/.agent_settings.json` | Slack channel + agent config | `setup.sh` / `slack_interface.py config` |
| `/root/.claude/settings.json` | LiteLLM API key + model config | Platform (`ninja_cline_setup.sh`) |
| `/dev/shm/mcp-token` | Slack + GitHub tokens | Platform (at sandbox startup) |
| `settings.json` (in repo) | Auto-generated LiteLLM settings | `orchestrator.py` (on first run) |
| `memory/phantom_memory.md` | Agent's persistent memory | Agent (updated after each session) |

---

## Common Deployment Scenarios

### Scenario 1: Fresh sandbox, deploy everything
```bash
git clone https://github.com/Sodiride123/browser-automation.git /workspace/browser-automation
cd /workspace/browser-automation
bash setup.sh --channel "#browser-automation-test" --agent phantom
```

### Scenario 2: Repo already cloned, just reconfigure
```bash
cd /workspace/browser-automation
bash setup.sh --skip-install --channel "#new-channel" --agent phantom
```

### Scenario 3: Setup only, start orchestrator manually later
```bash
cd /workspace/browser-automation
bash setup.sh --channel "#browser-automation-test" --agent phantom --no-start

# ... do other things ...

# Start orchestrator when ready
python3 orchestrator.py
```

### Scenario 4: Debug — check what's running
```bash
supervisorctl status                          # All services
tail -f /workspace/logs/orchestrator.log      # Orchestrator logs
python3 slack_interface.py config             # Current Slack config
python3 slack_interface.py scopes             # Token validity
python3 slack_interface.py read --limit 5     # Recent messages
python3 phantom/browser_server.py status      # Browser status
```

---

## Troubleshooting

### Bot doesn't respond to Slack messages

1. **Check if bot is in the channel:**
   ```bash
   python3 slack_interface.py read --limit 5
   ```
   If it returns "0 messages", the bot isn't a member. Fix:
   - In Slack, type `/invite @superninja` in the channel
   - Or re-run: `python3 slack_interface.py config --set-channel "#channel-name"`
     (this auto-joins the channel)

2. **Check if orchestrator is running:**
   ```bash
   ps aux | grep orchestrator
   tail -20 /workspace/logs/orchestrator.log
   ```

3. **Check for rate limiting:**
   ```bash
   python3 -c "
   from slack_interface import SlackInterface
   s = SlackInterface()
   print(s.get_history(limit=1))
   "
   ```
   If you see "ratelimited", wait 2-3 minutes.

### VNC shows "connection refused"

```bash
# Check if services are running
supervisorctl status x11vnc novnc

# Restart if needed
supervisorctl restart x11vnc novnc

# Verify ports
ss -tlnp | grep -E "5901|6080"
```

### VNC asks for a password

The platform's supervisor config may launch x11vnc with `-rfbauth` instead of `-nopw`. The `install.sh` script patches this automatically, but if it wasn't run:

```bash
# Patch the platform config
sed -i 's/-rfbauth [^ ]*/-nopw/g' /etc/supervisor/conf.d/supervisord.conf
rm -f /root/.vnc/passwd /root/.vnc/password.txt
supervisorctl reread && supervisorctl update
supervisorctl restart x11vnc novnc
```

### Claude Code fails with "nested session" error

The `claude-wrapper.sh` must include `unset CLAUDECODE` before invoking Claude. This is already present in the repo. If you see this error, verify:

```bash
grep 'unset CLAUDECODE' claude-wrapper.sh
```

### Bot sends duplicate replies

Ensure only the Monitor process reads Slack. The work process task in `orchestrator.py` must NOT contain instructions to read Slack for messages. The default work task should say "Do NOT read Slack for new messages."

### Browser not connecting (CDP)

```bash
# Check browser server
python3 phantom/browser_server.py status

# Restart browser
supervisorctl restart phantom_browser

# Verify CDP port
curl -s http://localhost:9222/json/version
```

---

## For VM Image Builders

If you're preparing a clean VM image for distribution:

```bash
cd /workspace/browser-automation

# 1. Run the cleanup command
rm -rf phantom/browser_data/ phantom/screenshots/* phantom/psiphon_data/
rm -rf phantom/.browser_server.pid logs/* __pycache__/ phantom/__pycache__/
rm -f .seen_messages.json .agent_messages.json .orchestrator.lock settings.json

# 2. Reset memory
cat > memory/phantom_memory.md << 'EOF'
# Phantom Memory

## Session History
(No sessions yet)

## Known Sites
(Will be populated as Phantom visits sites)

## Selector Notes
(Will be populated as Phantom learns site selectors)

## Proxy Notes
- **Current proxy**: Psiphon tunnel core — local HTTP proxy on `localhost:18080`, SOCKS on `localhost:18081`

## VNC Notes
- Use `from phantom.vnc import get_vnc_url` to generate the URL programmatically

## Issues Encountered
(None yet)
EOF

# 3. Clean files outside the repo
rm -f /root/.agent_settings.json
rm -f /root/.vnc/passwd
rm -f /root/s3_config.json

# 4. Verify no secrets in tracked files
git status
git diff
```

Then snapshot the VM. On next boot, the user just runs:
```bash
cd /workspace/browser-automation
bash setup.sh --channel "#their-channel" --agent phantom
```
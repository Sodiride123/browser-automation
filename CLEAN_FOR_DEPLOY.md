# Clean Repo for Deployment

> Run these steps before distributing the repo or deploying to a new environment.

---

## Quick Clean Command

Copy-paste this single block to clean everything:

```bash
cd /workspace/browser-automation

# 1. Stop running processes
pkill -f 'orchestrator\.py' 2>/dev/null
pkill -f 'monitor\.py' 2>/dev/null

# 2. Remove runtime state files
rm -f .seen_messages.json .agent_messages.json
rm -f .orchestrator.lock .monitor.lock
rm -f settings.json

# 3. Remove browser data (cookies, cache, login sessions — ~200MB)
rm -rf phantom/browser_data/
rm -f phantom/.browser_server.pid

# 4. Remove screenshots and reports
rm -rf phantom/screenshots/*
rm -rf reports/*

# 5. Remove proxy/tunnel data and binary
rm -rf phantom/psiphon_data/
rm -f phantom/psiphon-tunnel-core
rm -f phantom/remote_server_list*

# 6. Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# 7. Remove logs
rm -rf logs/*

# 8. Remove GitHub CLI config (contains tokens)
rm -rf .config/

# 9. Remove Claude Code local settings
rm -rf .claude/

# 10. Reset agent memory to blank template
cat > memory/phantom_memory.md << 'MEMEOF'
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
MEMEOF

# 11. Remove batch dedup temp files
rm -rf /tmp/phantom_batch_dedup/

# 12. Remove files outside the repo that are environment-specific
rm -f /root/.agent_settings.json
rm -f /root/.vnc/passwd /root/.vnc/password.txt
rm -f /root/s3_config.json
```

---

## What Each File/Directory Is

### Runtime State (must delete)

| Path | What It Is |
|------|-----------|
| `.seen_messages.json` | Tracks which Slack messages the monitor has already processed |
| `.agent_messages.json` | Tracks agent's own Slack messages for thread monitoring |
| `.orchestrator.lock` | PID lock preventing duplicate orchestrator instances |
| `.monitor.lock` | PID lock preventing duplicate monitor instances |
| `settings.json` | Auto-generated from `/root/.claude/settings.json` — contains API tokens |

### Browser Data (must delete, ~200MB)

| Path | What It Is |
|------|-----------|
| `phantom/browser_data/` | Chromium user profile — cookies, cache, IndexedDB, session storage, login sessions |
| `phantom/.browser_server.pid` | PID file for the persistent Chromium process |
| `phantom/screenshots/` | Screenshots taken during task execution (step_000.png, step_001.png, ...) |

### Proxy/Tunnel (must delete)

| Path | What It Is |
|------|-----------|
| `phantom/psiphon_data/` | Psiphon tunnel runtime data (datastore, OSL configs) |
| `phantom/psiphon-tunnel-core` | Psiphon binary (~9MB), downloaded by `install.sh` at setup time |
| `phantom/remote_server_list*` | Psiphon server lists |

### Reports & Logs (must delete)

| Path | What It Is |
|------|-----------|
| `reports/*.png` | Task screenshots — may contain **sensitive content** (Gmail inbox, search results, login pages, etc.). Keep `reports/.gitkeep`. |
| `logs/*` | Daily log files (orchestrator, phantom, etc.) |

### Python Cache (must delete)

| Path | What It Is |
|------|-----------|
| `__pycache__/` | Compiled Python bytecode (in root, phantom/, utils/) |

### Config & Credentials (must delete)

| Path | What It Is |
|------|-----------|
| `.config/gh/` | GitHub CLI auth config (contains tokens) |
| `.claude/` | Claude Code local settings (permissions, session state) |

### Agent Memory (must reset)

| Path | What It Is |
|------|-----------|
| `memory/phantom_memory.md` | Persistent memory updated after each session — contains session history, user IDs, site selectors, and VNC URLs. Must reset to blank template, not delete. |

### Batch Dedup Temp Files (must delete)

| Path | What It Is |
|------|-----------|
| `/tmp/phantom_batch_dedup/` | Per-thread message counters used by the anti-duplicate guard in `slack_interface.py`. Created during batch mode, cleaned by the monitor before each cycle. |

### Files Outside the Repo (must delete on the machine)

| Path | What It Is |
|------|-----------|
| `/root/.agent_settings.json` | Slack channel, agent identity, cached bot token |
| `/root/.vnc/passwd` | VNC password file (should not exist in clean deploys) |
| `/root/s3_config.json` | S3 cache credentials |

---

## Files That Should NOT Be Deleted

These are part of the repo and needed for deployment:

- `reports/.gitkeep` — keeps the reports/ directory in git
- `memory/` directory itself — needed, just reset the content
- `logs/` directory itself — created by orchestrator at startup if missing
- `phantom/psiphon.config.json` — Psiphon config template (not runtime data)
- All `.py`, `.sh`, `.md` source files
- `avatars/`, `dashboard/`, `supervisor/`, `agent-docs/`, `utils/`
- `.gitignore`, `requirements.txt`

---

## Verification After Cleaning

```bash
# Should show only source files, no runtime data
git status

# Should be ~5MB or less (no browser_data, no psiphon binary)
du -sh --exclude=.git .

# These should NOT exist
ls .seen_messages.json .agent_messages.json .orchestrator.lock .monitor.lock settings.json 2>&1 | grep -c "No such file"
# Expected: 5

# These directories should be empty or absent
ls phantom/browser_data/ phantom/screenshots/ phantom/psiphon_data/ 2>&1 | grep -c "No such file"
# Expected: 3
```

---

## Documentation Gaps for Claude Code Deployment

> Target environment: **NinjaTech sandbox** (supervisord, Xvfb, VNC, LiteLLM, tokens all pre-provisioned).

The existing docs (README.md, DEPLOY.md, CODEBASE_GUIDE.md) cover most of what's needed. Since the sandbox provides OS packages, supervisord services, tokens at `/dev/shm/mcp-token`, and `/root/.claude/settings.json`, the main remaining gaps are:

### Gaps Worth Fixing

1. **`settings.json` auto-generation not explained** — `orchestrator.py` generates `settings.json` from `/root/.claude/settings.json` on every start. If the Claude settings file is missing or malformed, orchestrator exits with a vague error. DEPLOY.md should mention this dependency and how to debug it (`cat /root/.claude/settings.json`).

2. **No post-deployment verification checklist** — After `setup.sh` finishes, there's no step-by-step way to confirm everything works. A simple checklist would help:
   ```
   supervisorctl status                          # All services running?
   curl -s http://localhost:9222/json/version     # Browser CDP alive?
   python3 slack_interface.py scopes              # Slack token valid?
   python3 slack_interface.py read --limit 1      # Can read channel?
   ps aux | grep orchestrator                     # Orchestrator running?
   tail -5 /workspace/logs/orchestrator.log       # No errors?
   ```

3. **Error recovery for partial failures** — If `setup.sh` fails midway (e.g., Psiphon download fails, Slack token not yet provisioned), docs don't say whether it's safe to rerun. It is — `setup.sh` is mostly idempotent — but stating this explicitly would help.

4. **Lock file recovery undocumented** — If orchestrator crashes, `.orchestrator.lock` remains and blocks restart. Recovery is just `rm .orchestrator.lock`, but a Claude Code agent won't know that without being told.

5. **Monitor architecture not mentioned in DEPLOY.md** — The dual-process design (Work + Monitor) and the single-instance lock on `monitor.py` are important for debugging "bot not responding" issues but only documented in CODEBASE_GUIDE.md.

### Already Well Covered

- Clone + `setup.sh` one-command deploy flow
- Token provisioning via `/dev/shm/mcp-token`
- Service ports table
- VNC password patching
- Slack troubleshooting basics
- VM image building cleanup steps

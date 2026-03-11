# WAKE UP Schedule — Git Auto-Commit Step

## Overview

Every 30 minutes, the WAKE UP prompt runs. A git auto-commit step has been added **between step 1 (GitHub login) and step 2 (kill/restart orchestrator)**.

This ensures that code, logs, and memory changes are committed and pushed to the `status-update-from-phantom` branch before the orchestrator restarts.

---

## Updated WAKE UP Schedule

```
WAKE UP:
Important: do not send any message in Slack for the "WAKE UP"

1- Login to GitHub using /dev/shm/mcp-token

1.5- Run git auto-commit (NEW STEP):
     bash /workspace/browser-automation/git_auto_commit.sh

2- Kill any existing orchestrator, clear the lock file, then start orchestrator.py in non-blocking mode

3- Provide link to your dashboard and VNC
```

---

## What the Script Does

1. **Checks GitHub authentication** — if the user hasn't connected GitHub, it skips silently
2. **Checks if the repo exists** — creates it if missing
3. **Checks if `status-update-from-phantom` branch exists** — creates it if missing
4. **Stages all changes** (respecting `.gitignore` — excludes cache, includes code/logs/memory)
5. **Checks for actual differences** — if nothing changed, skips commit
6. **Generates a commit message** from the diff summary (categorized by code/logs/memory/config)
7. **Commits and pushes** to `origin/status-update-from-phantom`

---

## What Is Included vs Excluded

### ✅ Included (committed)
- All Python source code (`*.py`)
- Shell scripts (`*.sh`)
- Documentation (`*.md`)
- Configuration files (non-sensitive)
- `logs/` directory — operational logs
- `memory/phantom_memory.md` — agent memory
- `dashboard/` — dashboard app
- `agent-docs/` — policy documents
- `utils/` — utility library

### ❌ Excluded (in .gitignore)
- `phantom/browser_data/` — browser cookies, cache, profiles
- `phantom/screenshots/` — runtime screenshots (large binaries)
- `phantom/psiphon_data/` — proxy tunnel state
- `__pycache__/` — Python bytecode
- `*.pyc`, `*.pyo` — compiled Python
- `reports/` — task output artifacts
- `.orchestrator.lock` — runtime lock file
- `settings.json` — auto-generated API config
- Token/secret files — security sensitive
- `.env` files — environment variables

---

## Manual Run

You can run the script manually at any time:

```bash
bash /workspace/browser-automation/git_auto_commit.sh
```

---

## Branch Strategy

All Phantom's automated commits go to the `status-update-from-phantom` branch, keeping `main` clean. This makes it easy to:
- Review what the agent changed over time
- Cherry-pick specific updates to main if needed
- Reset the branch without affecting the main codebase
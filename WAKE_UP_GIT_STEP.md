# WAKE UP Schedule — Git Auto-Commit Step

## Overview

Every 30 minutes, the WAKE UP prompt runs. A git auto-commit step has been added **between step 1 (GitHub login) and step 2 (kill/restart orchestrator)**.

This ensures that code, logs, and memory changes are committed and pushed to the `status-update-from-phantom` branch before the orchestrator restarts.

---

## Session Configuration via `.env`

The `stage1_install.sh` script accepts two optional arguments that are saved to `.env`:

```bash
bash /workspace/browser-automation/stage1_install.sh \
    --slack-channel "#test_phantom2" \
    --repo-name "browser-automation"
```

This writes `/workspace/browser-automation/.env`:
```
SLACK_CHANNEL="#test_phantom2"
REPO_NAME="browser-automation"
```

Both `git_auto_commit.sh` and `stage2_start.sh` read from this file automatically — no hardcoded values.

**Priority chain for REPO_NAME:**
1. `.env` file (written by `stage1_install.sh --repo-name`)
2. Git remote URL (inferred from `origin`)
3. Directory name (final fallback)

**Priority chain for SLACK_CHANNEL:**
1. `$1` argument to `stage2_start.sh` (explicit override)
2. `.env` file (written by `stage1_install.sh --slack-channel`)
3. `#browser-automation-test` (hardcoded fallback)

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
2. **Reads REPO_NAME from `.env`** — falls back to git remote or directory name
3. **Checks if the repo exists** — creates it if missing
4. **Checks if `status-update-from-phantom` branch exists** — creates it if missing
5. **Stages all changes** (respecting `.gitignore` — excludes cache, includes code/logs/memory)
6. **Checks for actual differences** — if nothing changed, skips commit
7. **Generates a commit message** from the diff summary (categorized by code/logs/memory/config)
8. **Commits and pushes** to `origin/status-update-from-phantom`

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
- `.env` — session-specific config (contains no secrets, but is sandbox-specific)
- Token/secret files — security sensitive

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
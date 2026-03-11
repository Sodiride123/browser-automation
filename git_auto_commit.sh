#!/usr/bin/env bash
# =============================================================================
#  git_auto_commit.sh — Automated Git Commit & Push for Phantom
# =============================================================================
#  Purpose:  Commit code, logs, and memory changes to a dedicated branch
#            (status-update-from-phantom) every 30 minutes.
#
#  Usage:    bash /workspace/browser-automation/git_auto_commit.sh
#
#  Designed to run between step 1 (GitHub login) and step 2 (orchestrator start)
#  of the WAKE UP schedule.
#
#  Exit codes:
#    0  — Success (committed + pushed, or no changes to commit)
#    1  — GitHub not authenticated or not connected
#    2  — Error during git operations
# =============================================================================

set -euo pipefail

REPO_DIR="/workspace/browser-automation"
BRANCH="status-update-from-phantom"
ENV_FILE="$REPO_DIR/.env"

# Read REPO_NAME from .env (written by stage1_install.sh)
REPO_NAME=""
if [ -f "$ENV_FILE" ]; then
    REPO_NAME=$(grep "^REPO_NAME=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '"' || true)
fi

# Fallback: infer from git remote if .env doesn't have it
if [ -z "$REPO_NAME" ]; then
    REPO_NAME=$(cd "$REPO_DIR" && git remote get-url origin 2>/dev/null | sed 's|.*/||; s|\.git$||' || true)
fi

# Final fallback: use directory name
if [ -z "$REPO_NAME" ]; then
    REPO_NAME=$(basename "$REPO_DIR")
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()  { echo -e "${CYAN}[git-auto]${NC} $*"; }
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $*"; }
err()  { echo -e "${RED}  ✗${NC} $*"; }

cd "$REPO_DIR"

echo ""
echo "============================================================"
echo "  Git Auto-Commit — Phantom Status Update"
echo "============================================================"
echo ""

# ─────────────────────────────────────────────────────────────────
# Step 0: Check GitHub authentication
# ─────────────────────────────────────────────────────────────────
log "Checking GitHub authentication..."

if ! gh auth status &>/dev/null; then
    warn "GitHub not authenticated — skipping commit & push"
    warn "User has not connected their GitHub account"
    exit 1
fi

GH_USER=$(gh api user --jq '.login' 2>/dev/null || echo "")
if [ -z "$GH_USER" ]; then
    warn "Could not determine GitHub username — skipping"
    exit 1
fi
ok "Authenticated as: $GH_USER"

# Ensure gh is configured as git credential helper
gh auth setup-git 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────
# Step 1: Check if the repository exists on GitHub
# ─────────────────────────────────────────────────────────────────
log "Checking if repo '$GH_USER/$REPO_NAME' exists on GitHub..."

REPO_EXISTS=false
if gh repo view "$GH_USER/$REPO_NAME" &>/dev/null; then
    REPO_EXISTS=true
    ok "Repository exists: $GH_USER/$REPO_NAME"
else
    warn "Repository '$GH_USER/$REPO_NAME' not found — creating it..."
    if gh repo create "$GH_USER/$REPO_NAME" --private --source="$REPO_DIR" --push 2>/dev/null; then
        ok "Repository created: $GH_USER/$REPO_NAME"
    else
        # If --source fails (e.g. remote already set), just create the repo
        gh repo create "$GH_USER/$REPO_NAME" --private 2>/dev/null || true
        ok "Repository created: $GH_USER/$REPO_NAME"
    fi
fi

# ─────────────────────────────────────────────────────────────────
# Step 1.5: Ensure remote origin points to the correct repo
# ─────────────────────────────────────────────────────────────────
EXPECTED_REMOTE="https://github.com/$GH_USER/$REPO_NAME.git"
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")

if [ "$CURRENT_REMOTE" != "$EXPECTED_REMOTE" ]; then
    log "Updating remote origin to $EXPECTED_REMOTE"
    git remote set-url origin "$EXPECTED_REMOTE" 2>/dev/null || git remote add origin "$EXPECTED_REMOTE"
    ok "Remote origin updated"
fi

# ─────────────────────────────────────────────────────────────────
# Step 2: Ensure we are on the correct branch
# ─────────────────────────────────────────────────────────────────
log "Checking branch '$BRANCH'..."

# Fetch remote branches
git fetch origin --prune 2>/dev/null || true

# Check if branch exists remotely
REMOTE_BRANCH_EXISTS=false
if git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH"; then
    REMOTE_BRANCH_EXISTS=true
fi

# Check if branch exists locally
LOCAL_BRANCH_EXISTS=false
if git show-ref --verify --quiet "refs/heads/$BRANCH" 2>/dev/null; then
    LOCAL_BRANCH_EXISTS=true
fi

if [ "$LOCAL_BRANCH_EXISTS" = true ]; then
    # Branch exists locally — switch to it
    git checkout "$BRANCH" 2>/dev/null
    ok "Switched to existing local branch: $BRANCH"
    
    # Pull latest if remote exists
    if [ "$REMOTE_BRANCH_EXISTS" = true ]; then
        git pull origin "$BRANCH" --rebase 2>/dev/null || true
    fi
elif [ "$REMOTE_BRANCH_EXISTS" = true ]; then
    # Branch exists only on remote — check it out
    git checkout -b "$BRANCH" "origin/$BRANCH" 2>/dev/null
    ok "Checked out remote branch: $BRANCH"
else
    # Branch doesn't exist anywhere — create from current HEAD
    # First, make sure we're not in detached HEAD by creating the branch from current commit
    git checkout -b "$BRANCH" 2>/dev/null
    ok "Created new branch: $BRANCH"
fi

# ─────────────────────────────────────────────────────────────────
# Step 3: Stage changes (respecting .gitignore)
# ─────────────────────────────────────────────────────────────────
log "Staging changes..."

# Ensure logs directory has a .gitkeep so it's always tracked
touch "$REPO_DIR/logs/.gitkeep" 2>/dev/null || true

# Stage everything (gitignore handles exclusions)
git add -A

# ─────────────────────────────────────────────────────────────────
# Step 4: Check if there are actual changes to commit
# ─────────────────────────────────────────────────────────────────
if git diff --cached --quiet; then
    ok "No changes detected — nothing to commit"
    echo ""
    echo "============================================================"
    echo "  ✅ Git Auto-Commit — No changes to push"
    echo "============================================================"
    echo ""
    exit 0
fi

# ─────────────────────────────────────────────────────────────────
# Step 5: Generate commit message from diff
# ─────────────────────────────────────────────────────────────────
log "Generating commit message from diff..."

# Get diff stats
DIFF_STAT=$(git diff --cached --stat --stat-width=60 2>/dev/null | tail -1)
FILES_CHANGED=$(git diff --cached --name-only 2>/dev/null)
NUM_FILES=$(echo "$FILES_CHANGED" | wc -l | tr -d ' ')

# Categorize changes
LOGS_CHANGED=$(echo "$FILES_CHANGED" | grep -c "^logs/" || true)
MEMORY_CHANGED=$(echo "$FILES_CHANGED" | grep -c "^memory/" || true)
CODE_CHANGED=$(echo "$FILES_CHANGED" | grep -cE '\.(py|sh|md|json|html|css|js)$' || true)
CONFIG_CHANGED=$(echo "$FILES_CHANGED" | grep -cE '\.gitignore|supervisord|\.conf$' || true)

# Build commit message
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')
COMMIT_SUBJECT="🔄 status update: $TIMESTAMP"

# Build body with categories
COMMIT_BODY="Automated 30-min status update from Phantom agent.

Changes summary ($DIFF_STAT):
"

if [ "$CODE_CHANGED" -gt 0 ]; then
    COMMIT_BODY+="- Code/docs: $CODE_CHANGED file(s) modified
"
fi
if [ "$LOGS_CHANGED" -gt 0 ]; then
    COMMIT_BODY+="- Logs: $LOGS_CHANGED file(s) updated
"
fi
if [ "$MEMORY_CHANGED" -gt 0 ]; then
    COMMIT_BODY+="- Memory: $MEMORY_CHANGED file(s) updated
"
fi
if [ "$CONFIG_CHANGED" -gt 0 ]; then
    COMMIT_BODY+="- Config: $CONFIG_CHANGED file(s) changed
"
fi

COMMIT_BODY+="
Files changed:
$(echo "$FILES_CHANGED" | sed 's/^/  - /')"

# ─────────────────────────────────────────────────────────────────
# Step 6: Commit and push
# ─────────────────────────────────────────────────────────────────
log "Committing changes..."

git -c user.name="Phantom Agent" -c user.email="phantom@ninjatech.ai" \
    commit -m "$COMMIT_SUBJECT" -m "$COMMIT_BODY"

ok "Committed: $COMMIT_SUBJECT"

log "Pushing to origin/$BRANCH..."

git push origin "$BRANCH" 2>&1

ok "Pushed to origin/$BRANCH"

echo ""
echo "============================================================"
echo "  ✅ Git Auto-Commit — Successfully pushed!"
echo "============================================================"
echo "  Branch:  $BRANCH"
echo "  Files:   $NUM_FILES changed"
echo "  Remote:  https://github.com/$GH_USER/$REPO_NAME/tree/$BRANCH"
echo "============================================================"
echo ""

exit 0
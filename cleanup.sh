#!/usr/bin/env bash
# =============================================================================
# cleanup.sh — Reset Phantom to a clean state for new deployment
# =============================================================================
# Run this before:
#   - Creating a new VM image for distribution
#   - Handing off the environment to a new user
#   - Starting a completely fresh deployment
#
# See CLEANUP_BEFORE_DEPLOY.md for full explanation of each item.
#
# Usage:
#   chmod +x cleanup.sh
#   ./cleanup.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "============================================================"
echo "  Phantom — Cleanup for Fresh Deployment"
echo "============================================================"
echo ""

# --- 🔴 Critical: Personal / session data ------------------------------------
echo "▶ Removing personal & session data..."

# Browser profile (cookies, login sessions, history)
rm -rf "$SCRIPT_DIR/phantom/browser_data/"
mkdir -p "$SCRIPT_DIR/phantom/browser_data/"
echo "  ✓ phantom/browser_data/ cleared"

# Step-by-step screenshots from previous tasks
rm -rf "$SCRIPT_DIR/phantom/screenshots/"
mkdir -p "$SCRIPT_DIR/phantom/screenshots/"
echo "  ✓ phantom/screenshots/ cleared"

# Psiphon tunnel state and server cache
rm -rf "$SCRIPT_DIR/phantom/psiphon_data/"
mkdir -p "$SCRIPT_DIR/phantom/psiphon_data/"
echo "  ✓ phantom/psiphon_data/ cleared"

# Agent memory (task history, site knowledge, personal data)
rm -f "$SCRIPT_DIR/memory/phantom_memory.md"
printf "# Phantom Memory\n\n## Session History\n\n## Known Sites\n" \
    > "$SCRIPT_DIR/memory/phantom_memory.md"
echo "  ✓ memory/phantom_memory.md reset to blank"

# --- 🟠 Important: Logs and runtime cache ------------------------------------
echo "▶ Removing logs and runtime cache..."

# Application and orchestrator logs
rm -rf "$SCRIPT_DIR/logs/"
mkdir -p "$SCRIPT_DIR/logs/"
echo "  ✓ logs/ cleared"

# Slack agent config (workspace, channel ID, cached bot token)
rm -f /root/.agent_settings.json
echo "  ✓ /root/.agent_settings.json removed"

# Orchestrator lock file (prevents stale lock from blocking startup)
rm -f "$SCRIPT_DIR/.orchestrator.lock"
echo "  ✓ .orchestrator.lock removed"

# Generated settings.json (recreated by orchestrator from /root/.claude/settings.json)
rm -f "$SCRIPT_DIR/settings.json"
echo "  ✓ settings.json removed"

# --- 🟡 Optional: Task artifacts ---------------------------------------------
echo "▶ Removing task artifacts..."

rm -rf "$SCRIPT_DIR/reports/"
mkdir -p "$SCRIPT_DIR/reports/"
echo "  ✓ reports/ cleared"

# --- Python bytecode cache ---------------------------------------------------
echo "▶ Removing Python bytecode cache..."
find "$SCRIPT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$SCRIPT_DIR" -name "*.pyo" -delete 2>/dev/null || true
echo "  ✓ __pycache__ and .pyc files removed"

# --- Summary -----------------------------------------------------------------
echo ""
echo "============================================================"
echo "  ✅ Cleanup complete — environment is clean!"
echo "============================================================"
echo ""
echo "  What was cleared:"
echo "    🔴 phantom/browser_data/     (login sessions & cookies)"
echo "    🔴 phantom/screenshots/      (task screenshots)"
echo "    🔴 phantom/psiphon_data/     (proxy tunnel state)"
echo "    🔴 memory/phantom_memory.md  (agent memory — reset to blank)"
echo "    🟠 logs/                     (application logs)"
echo "    🟠 /root/.agent_settings.json (Slack workspace config)"
echo "    🟠 .orchestrator.lock        (stale lock file)"
echo "    🟠 settings.json             (generated API config)"
echo "    🟡 reports/                  (task output files)"
echo "    🟡 **/__pycache__/           (Python bytecode)"
echo ""
echo "  Next steps:"
echo "    • To create a VM image: snapshot now (after stage1_install.sh)"
echo "    • To start the app:     ./stage2_start.sh"
echo ""
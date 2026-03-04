#!/usr/bin/env bash
# stage1_install.sh — Install all dependencies on a clean sandbox, then prepare for snapshotting.
#
# Run this ONCE on a fresh sandbox, then snapshot the image for distribution.
# Users of the image then run stage2_configure.sh to configure and start.
#
# Usage:
#   bash stage1_install.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  📦 Stage 1: Install Dependencies + Prepare Image           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# --- Step 1: Run install.sh ------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 1/4: Installing dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash install.sh
echo ""

# --- Step 2: Verify services start correctly --------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2/4: Verifying services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sleep 3

check_service() {
    local name="$1"
    local port="$2"
    if ss -tlnp 2>/dev/null | grep -q ":${port} " || netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
        echo "  ✅ $name — port $port listening"
        return 0
    else
        echo "  ⚠️  $name — port $port NOT listening"
        return 1
    fi
}

SERVICES_OK=true
check_service "x11vnc"        "5901" || SERVICES_OK=false
check_service "noVNC"         "6080" || SERVICES_OK=false
check_service "Browser (CDP)" "9222" || SERVICES_OK=false
check_service "Dashboard"     "9000" || SERVICES_OK=false
check_service "Psiphon HTTP"  "18080" 2>/dev/null || echo "  ℹ️  Psiphon may still be starting"

if [ "$SERVICES_OK" = false ]; then
    echo ""
    echo "  ⚠️  Some services are not running. Attempting restart..."
    supervisorctl restart all 2>/dev/null || true
    sleep 5
    check_service "x11vnc"        "5901" || true
    check_service "noVNC"         "6080" || true
    check_service "Browser (CDP)" "9222" || true
    check_service "Dashboard"     "9000" || true
fi
echo ""

# --- Step 3: Stop services cleanly -----------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3/4: Stopping services for clean snapshot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Stop orchestrator/monitor if running
pkill -f 'orchestrator\.py' 2>/dev/null || true
pkill -f 'monitor\.py' 2>/dev/null || true

echo "  ✅ Processes stopped"
echo ""

# --- Step 4: Clean temp files -----------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 4/4: Cleaning temp files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Runtime state
rm -f .seen_messages.json .agent_messages.json
rm -f .orchestrator.lock .monitor.lock
rm -f settings.json

# Browser data (cookies, cache — user will log in fresh)
rm -rf phantom/browser_data/
rm -f phantom/.browser_server.pid

# Screenshots, reports, logs
rm -rf phantom/screenshots/*
rm -rf reports/*
rm -rf logs/*

# Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Batch dedup temp files
rm -rf /tmp/phantom_batch_dedup/

# Claude Code local settings
rm -rf .claude/

# GitHub CLI config
rm -rf .config/

# Agent settings (will be recreated by stage2)
rm -f /root/.agent_settings.json

# Reset memory to blank template
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

echo "  ✅ Temp files cleaned"
echo "  ✅ Memory reset to blank template"
echo ""

# --- Summary ----------------------------------------------------------------
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✅ Stage 1 Complete — Image Ready to Snapshot!             ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  What was installed:                                       ║"
echo "║    • Python packages (requirements.txt)                    ║"
echo "║    • Playwright + Chromium browser                         ║"
echo "║    • Psiphon proxy                                         ║"
echo "║    • Supervisord configs (VNC, browser, dashboard)         ║"
echo "║    • Platform browser_api.py patch (CDP)                   ║"
echo "║                                                            ║"
echo "║  Next steps:                                               ║"
echo "║    1. Snapshot this sandbox as an image                    ║"
echo "║    2. Share the image with users                           ║"
echo "║    3. Users run: bash stage2_configure.sh                  ║"
echo "║                  --channel \"#channel\" --agent phantom      ║"
echo "║                                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

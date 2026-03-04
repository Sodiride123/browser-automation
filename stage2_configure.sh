#!/usr/bin/env bash
# stage2_configure.sh — Configure Slack and start the orchestrator on a pre-installed image.
#
# This script is designed to run on a sandbox image where stage1_install.sh
# (or install.sh) has already been run. It skips dependency installation and
# goes straight to service verification, Slack configuration, and orchestrator startup.
#
# Usage:
#   bash stage2_configure.sh --channel "#my-channel" --agent phantom
#   bash stage2_configure.sh                            # Interactive — prompts for channel/agent
#   bash stage2_configure.sh --no-start                 # Configure only, don't start orchestrator
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Defaults ---------------------------------------------------------------
CHANNEL=""
AGENT=""
NO_START=false
NON_INTERACTIVE=false

# --- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --channel|-c)   CHANNEL="$2"; shift 2 ;;
        --agent|-a)     AGENT="$2"; shift 2 ;;
        --no-start)     NO_START=true; shift ;;
        --yes|-y)       NON_INTERACTIVE=true; shift ;;
        --help|-h)
            echo "Usage: bash stage2_configure.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --channel, -c CHANNEL   Slack channel (e.g., '#my-channel')"
            echo "  --agent, -a AGENT       Agent name (e.g., 'phantom')"
            echo "  --no-start              Don't start orchestrator after setup"
            echo "  --yes, -y               Non-interactive mode (skip all prompts)"
            echo "  --help, -h              Show this help"
            exit 0
            ;;
        *) echo "❌ Unknown option: $1"; exit 1 ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  🚀 Stage 2: Configure & Start (pre-installed image)        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# --- Step 1: Restart services ----------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 1/4: Starting services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Ensure supervisord is running
if ! pgrep -x supervisord > /dev/null 2>&1; then
    supervisord -c /etc/supervisor/supervisord.conf 2>/dev/null || true
    sleep 2
fi

supervisorctl reread 2>/dev/null || true
supervisorctl update 2>/dev/null || true
supervisorctl start all 2>/dev/null || true
sleep 3

echo "  ✅ Services started"
echo ""

# --- Step 2: Verify services ------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2/4: Verifying services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

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

# --- Step 3: Check tokens + configure Slack ---------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3/4: Configuring Slack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check tokens
TOKEN_FILE="/dev/shm/mcp-token"
if [ -f "$TOKEN_FILE" ]; then
    echo "  ✅ Token file found: $TOKEN_FILE"
    if grep -q "Slack=" "$TOKEN_FILE" 2>/dev/null; then
        echo "  ✅ Slack tokens present"
    else
        echo "  ⚠️  Slack tokens not found in $TOKEN_FILE"
    fi
    if grep -q "Github=" "$TOKEN_FILE" 2>/dev/null; then
        echo "  ✅ GitHub token present"
    fi
else
    echo "  ⚠️  Token file not found: $TOKEN_FILE"
    echo "     Slack tokens are provided by the platform at runtime."
    echo "     If running locally, set SLACK_BOT_TOKEN and SLACK_APP_TOKEN env vars."
fi

# Verify Slack scopes
echo ""
echo "  Verifying Slack connection..."
SCOPE_OUTPUT=$(python3 slack_interface.py scopes 2>&1) || true
if echo "$SCOPE_OUTPUT" | grep -q "channels:read"; then
    echo "  ✅ Slack bot token is valid"
else
    echo "  ⚠️  Could not verify Slack scopes — token may not be loaded yet"
    echo "     Output: ${SCOPE_OUTPUT:0:200}"
fi

# Auto-enable non-interactive if both channel and agent are provided
if [ -n "$CHANNEL" ] && [ -n "$AGENT" ]; then
    NON_INTERACTIVE=true
fi

# Prompt for channel if not provided
if [ -z "$CHANNEL" ]; then
    if [ "$NON_INTERACTIVE" = true ]; then
        echo "  ❌ --channel is required in non-interactive mode"
        exit 1
    fi
    echo ""
    read -rp "  Enter Slack channel (e.g., #browser-automation-test): " CHANNEL
fi

# Prompt for agent if not provided
if [ -z "$AGENT" ]; then
    if [ "$NON_INTERACTIVE" = true ]; then
        AGENT="phantom"
        echo "  ℹ️  Defaulting agent to: phantom"
    else
        echo ""
        echo "  Available agents: phantom, nova, pixel, bolt, scout"
        read -rp "  Enter agent name (default: phantom): " AGENT
        AGENT="${AGENT:-phantom}"
    fi
fi

# Set channel and agent
echo ""
echo "  Setting channel: $CHANNEL"
echo "  Setting agent:   $AGENT"
python3 slack_interface.py config --set-channel "$CHANNEL" --set-agent "$AGENT" 2>&1 | sed 's/^/  /'

# Log into GitHub CLI if token available
if [ -f "$TOKEN_FILE" ] && grep -q "Github=" "$TOKEN_FILE" 2>/dev/null; then
    echo ""
    echo "  Logging into GitHub CLI..."
    GITHUB_TOKEN=$(python3 -c "
import json
for line in open('$TOKEN_FILE'):
    if line.startswith('Github='):
        data = json.loads(line.split('=', 1)[1])
        print(data.get('access_token', ''))
        break
" 2>/dev/null) || true
    if [ -n "$GITHUB_TOKEN" ]; then
        echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null && echo "  ✅ GitHub CLI authenticated" || echo "  ⚠️  GitHub CLI auth failed"
    fi
fi

# Verify message access
echo ""
echo "  Verifying message access..."
READ_OUTPUT=$(python3 slack_interface.py read --limit 1 2>&1) || true
if echo "$READ_OUTPUT" | grep -qi "no messages\|empty\|0 messages"; then
    echo "  ⚠️  Bot may not have access to $CHANNEL"
    echo "     If needed, run in Slack: /invite @superninja"
    if [ "$NON_INTERACTIVE" = false ]; then
        echo ""
        read -rp "  Press Enter after inviting the bot (or 's' to skip): " SKIP_VERIFY
        if [ "$SKIP_VERIFY" != "s" ]; then
            READ_OUTPUT=$(python3 slack_interface.py read --limit 1 2>&1) || true
            if echo "$READ_OUTPUT" | grep -qi "no messages\|empty\|0 messages"; then
                echo "  ⚠️  Still no messages — continuing anyway."
            else
                echo "  ✅ Bot can read messages from $CHANNEL"
            fi
        fi
    else
        echo "  ℹ️  Skipping prompt (non-interactive) — continuing anyway."
    fi
elif echo "$READ_OUTPUT" | grep -qi "ratelimit\|429"; then
    echo "  ⚠️  Rate limited — Slack access will work once rate limit clears"
else
    echo "  ✅ Bot can read messages from $CHANNEL"
fi

# Send online message
echo ""
echo "  Sending online notification to Slack..."
python3 slack_interface.py say "🤖 Phantom is online and ready!" 2>&1 | sed 's/^/  /' || true
echo ""

# --- Step 4: Start orchestrator --------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 4/4: Starting orchestrator"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Clean stale lock files
rm -f .orchestrator.lock .monitor.lock

# Create log directory
mkdir -p /workspace/logs

if [ "$NO_START" = true ]; then
    echo "  ⏭️  Skipping orchestrator start (--no-start)"
else
    echo "  Starting orchestrator in background..."
    nohup python3 orchestrator.py > /workspace/logs/orchestrator.log 2>&1 &
    ORCH_PID=$!
    sleep 3

    if kill -0 "$ORCH_PID" 2>/dev/null; then
        echo "  ✅ Orchestrator running (PID: $ORCH_PID)"
        echo "  📋 Logs: tail -f /workspace/logs/orchestrator.log"
    else
        echo "  ⚠️  Orchestrator may have exited — check logs:"
        echo "     tail -20 /workspace/logs/orchestrator.log"
    fi
fi

# --- Summary ----------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✅ Stage 2 Complete — Phantom is Running!                  ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  Services:                                                 ║"
echo "║    • Dashboard:  http://localhost:9000                     ║"
echo "║    • noVNC:      http://localhost:6080/vnc.html            ║"
echo "║    • Browser:    http://localhost:9222 (CDP)               ║"
echo "║                                                            ║"
echo "║  Slack:                                                    ║"
echo "║    • Channel:    $CHANNEL"
echo "║    • Agent:      $AGENT"
echo "║                                                            ║"
echo "║  Commands:                                                 ║"
echo "║    supervisorctl status          # Check services          ║"
echo "║    tail -f /workspace/logs/orchestrator.log  # Logs        ║"
echo "║    python3 orchestrator.py       # Restart orchestrator    ║"
echo "║                                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

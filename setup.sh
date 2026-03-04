#!/usr/bin/env bash
# setup.sh — Automated setup & onboarding for Phantom browser automation agent
#
# This script handles everything needed to get Phantom running on a fresh VM:
#   1. Runs install.sh (deps, Playwright, Psiphon, supervisord, VNC)
#   2. Verifies all services are running
#   3. Configures Slack (channel + agent)
#   4. Verifies Slack connectivity
#   5. Starts the orchestrator
#
# Usage:
#   bash setup.sh                                          # Interactive — prompts for channel/agent
#   bash setup.sh --channel "#my-channel" --agent phantom  # Non-interactive
#   bash setup.sh --skip-install                           # Skip install.sh (already ran)
#   bash setup.sh --no-start                               # Setup only, don't start orchestrator
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Defaults ---------------------------------------------------------------
CHANNEL=""
AGENT=""
SKIP_INSTALL=false
NO_START=false

# --- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --channel|-c)   CHANNEL="$2"; shift 2 ;;
        --agent|-a)     AGENT="$2"; shift 2 ;;
        --skip-install) SKIP_INSTALL=true; shift ;;
        --no-start)     NO_START=true; shift ;;
        --help|-h)
            echo "Usage: bash setup.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --channel, -c CHANNEL   Slack channel (e.g., '#my-channel')"
            echo "  --agent, -a AGENT       Agent name (e.g., 'phantom')"
            echo "  --skip-install          Skip install.sh (deps already installed)"
            echo "  --no-start              Don't start orchestrator after setup"
            echo "  --help, -h              Show this help"
            exit 0
            ;;
        *) echo "❌ Unknown option: $1"; exit 1 ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  🤖 Phantom Browser Automation — Automated Setup           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# --- Step 1: Run install.sh ------------------------------------------------
if [ "$SKIP_INSTALL" = false ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Step 1/5: Installing dependencies"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    bash install.sh
    echo ""
else
    echo "⏭️  Skipping install.sh (--skip-install)"
    echo ""
fi

# --- Step 2: Verify services -----------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2/5: Verifying services"
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

# Give services a moment to start
sleep 2

SERVICES_OK=true
check_service "Xvfb (display)"    "99"   2>/dev/null || true  # Xvfb uses display, not a TCP port
check_service "x11vnc"            "5901" || SERVICES_OK=false
check_service "noVNC"             "6080" || SERVICES_OK=false
check_service "Browser (CDP)"     "9222" || SERVICES_OK=false
check_service "Dashboard"         "9000" || SERVICES_OK=false

# Check Psiphon separately (may take longer to start)
if check_service "Psiphon HTTP"   "18080" 2>/dev/null; then
    true
else
    echo "  ℹ️  Psiphon may still be starting — this is normal"
fi

if [ "$SERVICES_OK" = false ]; then
    echo ""
    echo "  ⚠️  Some services are not running. Attempting restart..."
    supervisorctl restart all 2>/dev/null || true
    sleep 5
    echo "  Rechecking..."
    check_service "x11vnc"        "5901" || true
    check_service "noVNC"         "6080" || true
    check_service "Browser (CDP)" "9222" || true
    check_service "Dashboard"     "9000" || true
fi
echo ""

# --- Step 3: Check Slack tokens --------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3/5: Checking Slack tokens"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOKEN_FILE="/dev/shm/mcp-token"
if [ -f "$TOKEN_FILE" ]; then
    echo "  ✅ Token file found: $TOKEN_FILE"
    
    # Verify it contains Slack tokens
    if grep -q "Slack=" "$TOKEN_FILE" 2>/dev/null; then
        echo "  ✅ Slack tokens present"
    else
        echo "  ⚠️  Slack tokens not found in $TOKEN_FILE"
        echo "     The platform should provide these automatically."
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
echo ""

# --- Step 4: Configure Slack channel & agent --------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 4/5: Configuring Slack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Prompt for channel if not provided
if [ -z "$CHANNEL" ]; then
    echo ""
    read -rp "  Enter Slack channel (e.g., #browser-automation-test): " CHANNEL
fi

# Prompt for agent if not provided
if [ -z "$AGENT" ]; then
    echo ""
    echo "  Available agents: phantom, nova, pixel, bolt, scout"
    read -rp "  Enter agent name (default: phantom): " AGENT
    AGENT="${AGENT:-phantom}"
fi

# Set channel and agent together (our fix ensures both are processed)
echo ""
echo "  Setting channel: $CHANNEL"
echo "  Setting agent:   $AGENT"
python3 slack_interface.py config --set-channel "$CHANNEL" --set-agent "$AGENT" 2>&1 | sed 's/^/  /'

# Verify we can read messages
echo ""
echo "  Verifying message access..."
READ_OUTPUT=$(python3 slack_interface.py read --limit 1 2>&1) || true
if echo "$READ_OUTPUT" | grep -qi "no messages\|empty\|0 messages"; then
    echo "  ⚠️  Bot cannot read messages from $CHANNEL"
    echo "     This usually means the bot is not a member of the channel."
    echo "     Please run this in Slack: /invite @superninja"
    echo ""
    read -rp "  Press Enter after inviting the bot (or 's' to skip): " SKIP_VERIFY
    if [ "$SKIP_VERIFY" != "s" ]; then
        READ_OUTPUT=$(python3 slack_interface.py read --limit 1 2>&1) || true
        if echo "$READ_OUTPUT" | grep -qi "no messages\|empty\|0 messages"; then
            echo "  ⚠️  Still no messages — continuing anyway. Bot may need manual invite."
        else
            echo "  ✅ Bot can read messages from $CHANNEL"
        fi
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

# --- Step 5: Start orchestrator --------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 5/5: Starting orchestrator"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

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
echo "║  ✅ Setup Complete!                                         ║"
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
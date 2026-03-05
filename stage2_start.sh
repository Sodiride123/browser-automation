#!/usr/bin/env bash
# =============================================================================
# STAGE 2 — App Startup Script
# =============================================================================
# Purpose: Start the Phantom browser automation app on a VM image that already
#          has all dependencies installed (via stage1_install.sh).
#
# What this does:
#   1. Reads tokens from /dev/shm/mcp-token (Slack + GitHub)
#   2. Configures Slack agent identity (Phantom) and channel
#   3. Fixes /root/s3_config.json if needed (trailing comma bug)
#   4. Reloads supervisord services (browser, VNC, dashboard, proxy)
#   5. Waits for browser server to be ready (CDP on port 9222)
#   6. Prints VNC URL and Dashboard URL
#   7. Posts "Phantom is online" message to Slack
#   8. Starts orchestrator in background (work + monitor processes)
#
# Usage:
#   chmod +x stage2_start.sh
#   ./stage2_start.sh
#
# Prerequisites:
#   - stage1_install.sh must have been run on this image
#   - /dev/shm/mcp-token must exist with valid Slack + GitHub tokens
#   - Supervisord must be running (it is in SuperNinja sandboxes by default)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_TOKEN_FILE="/dev/shm/mcp-token"
S3_CONFIG="/root/s3_config.json"

echo ""
echo "============================================================"
echo "  Phantom Browser Automation — Stage 2: App Startup"
echo "============================================================"
echo ""

# --- 1. Verify dependencies are installed ------------------------------------
echo "▶ [1/8] Verifying Stage 1 dependencies..."

MISSING=0
for pkg in playwright flask requests boto3; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        echo "  ✗ Missing Python package: $pkg"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "  ❌ ERROR: $MISSING dependencies missing."
    echo "  Please run stage1_install.sh first to install all dependencies."
    echo ""
    exit 1
fi
echo "  ✓ All dependencies present"

# --- 2. Read tokens from /dev/shm/mcp-token ----------------------------------
echo "▶ [2/8] Reading tokens from $MCP_TOKEN_FILE..."

if [ ! -f "$MCP_TOKEN_FILE" ]; then
    echo "  ❌ ERROR: $MCP_TOKEN_FILE not found."
    echo "  Tokens are auto-populated when you open a SuperNinja sandbox."
    echo "  Make sure you are running inside a SuperNinja environment."
    exit 1
fi

# Extract bot token using Python (handles the key=JSON format)
BOT_TOKEN=$(python3 << 'PYEOF'
import re, json, sys

with open("/dev/shm/mcp-token", "r") as f:
    content = f.read()

# Parse Slack JSON block
slack_match = re.search(r'Slack=(\{.*?\})(?:\n|$)', content)
if not slack_match:
    print("ERROR: Could not find Slack token block", file=sys.stderr)
    sys.exit(1)

slack_data = json.loads(slack_match.group(1))
bot_token = slack_data.get("bot_token", "")

if not bot_token.startswith("xoxb-") and not bot_token.startswith("xoxe.xoxb-"):
    print("ERROR: Invalid bot token format", file=sys.stderr)
    sys.exit(1)

print(bot_token)
PYEOF
)

if [ -z "$BOT_TOKEN" ]; then
    echo "  ❌ ERROR: Could not extract Slack bot token from $MCP_TOKEN_FILE"
    exit 1
fi

echo "  ✓ Slack bot token found"

# --- 3. Fix /root/s3_config.json trailing comma bug --------------------------
echo "▶ [3/8] Validating /root/s3_config.json..."

if [ -f "$S3_CONFIG" ]; then
    python3 << 'PYEOF'
import json, re, sys

path = "/root/s3_config.json"
with open(path, "r") as f:
    raw = f.read()

# Remove trailing commas before } or ]
fixed = re.sub(r',\s*([}\]])', r'\1', raw)

try:
    json.loads(fixed)
    with open(path, "w") as f:
        f.write(fixed)
    print("  ✓ s3_config.json valid")
except json.JSONDecodeError as e:
    print(f"  ⚠ s3_config.json could not be fixed: {e} — Slack channel cache may not work")
PYEOF
else
    echo "  ⚠ /root/s3_config.json not found — Slack channel cache disabled (non-fatal)"
fi

# --- 4. Configure Slack agent identity and channel ---------------------------
echo "▶ [4/8] Configuring Slack agent identity..."

cd "$SCRIPT_DIR"

# Set agent to phantom
python3 slack_interface.py config --set-agent phantom
echo "  ✓ Agent set to: Phantom"

# Set default channel
python3 slack_interface.py config --set-channel "#browser-automation-test"
echo "  ✓ Channel set to: #browser-automation-test"

# --- 5. Reload supervisord services ------------------------------------------
echo "▶ [5/8] Starting/reloading supervisord services..."

if command -v supervisorctl &>/dev/null; then
    supervisorctl reread 2>/dev/null || true
    supervisorctl update 2>/dev/null || true

    # Start phantom services if not already running
    for svc in xvfb x11vnc novnc phantom_browser psiphon agent-dashboard; do
        STATUS=$(supervisorctl status "$svc" 2>/dev/null | awk '{print $2}' || echo "UNKNOWN")
        if [ "$STATUS" = "RUNNING" ]; then
            echo "  ✓ $svc: already running"
        else
            supervisorctl start "$svc" 2>/dev/null || true
            echo "  ↺ $svc: started"
        fi
    done
else
    echo "  ⚠ supervisorctl not found — starting browser server manually..."
    python3 "$SCRIPT_DIR/phantom/browser_server.py" start &
fi

# --- 6. Wait for browser server (CDP port 9222) ------------------------------
echo "▶ [6/8] Waiting for browser server on port 9222..."

MAX_WAIT=30
WAITED=0
while ! curl -sf http://localhost:9222/json/version > /dev/null 2>&1; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "  ⚠ Browser server not ready after ${MAX_WAIT}s — trying manual start..."
        cd "$SCRIPT_DIR" && python3 phantom/browser_server.py start &
        sleep 5
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "  ... waiting (${WAITED}s)"
done

# Verify
if curl -sf http://localhost:9222/json/version > /dev/null 2>&1; then
    CHROME_VER=$(curl -sf http://localhost:9222/json/version | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Browser','unknown'))" 2>/dev/null || echo "unknown")
    echo "  ✓ Browser server ready: $CHROME_VER"
else
    echo "  ⚠ Browser server may not be ready — orchestrator will retry"
fi

# --- 7. Print access URLs ----------------------------------------------------
echo "▶ [7/8] Generating access URLs..."

VNC_URL=$(cd "$SCRIPT_DIR" && python3 -c "from phantom.vnc import get_vnc_url; print(get_vnc_url())" 2>/dev/null || echo "VNC URL unavailable")
VNC_PASSWORD=$(cat ~/.vnc/password.txt 2>/dev/null || echo "no-password")

# Dashboard URL via sandbox metadata
DASHBOARD_URL=$(python3 << 'PYEOF'
import json, re
from pathlib import Path

meta_file = Path("/dev/shm/sandbox_metadata.json")
if meta_file.exists():
    try:
        data = json.loads(meta_file.read_text())
        sandbox_id = data.get("sandbox_id", "")
        stage = data.get("stage", "beta")
        if sandbox_id:
            print(f"https://9000-{sandbox_id}.app.super.{stage}myninja.ai")
            exit()
    except Exception:
        pass
print("http://localhost:9000  (expose port 9000 for public URL)")
PYEOF
)

echo ""
echo "  ┌─────────────────────────────────────────────────────┐"
echo "  │  🖥️  Dashboard : $DASHBOARD_URL"
echo "  │  👁️  VNC URL   : $VNC_URL"
echo "  │  🔑  VNC Pass  : $VNC_PASSWORD"
echo "  └─────────────────────────────────────────────────────┘"
echo ""

# --- 8. Post Slack notification and start orchestrator -----------------------
echo "▶ [8/8] Starting orchestrator..."

cd "$SCRIPT_DIR"

# Post online notification to Slack
python3 slack_interface.py say "👻 Phantom is online! 
🖥️ Dashboard: $DASHBOARD_URL
👁️ VNC: $VNC_URL" 2>/dev/null || echo "  ⚠ Slack notification failed (non-fatal)"

# Start orchestrator in background (non-blocking)
nohup python3 orchestrator.py >> /workspace/logs/orchestrator_startup.log 2>&1 &
ORCH_PID=$!

echo "  ✓ Orchestrator started (PID: $ORCH_PID)"
echo "  📝 Logs: /workspace/logs/"

echo ""
echo "============================================================"
echo "  ✅ Stage 2 Complete — Phantom is running!"
echo "============================================================"
echo ""
echo "  Orchestrator PID : $ORCH_PID"
echo "  Dashboard        : $DASHBOARD_URL"
echo "  VNC              : $VNC_URL"
echo "  VNC Password     : $VNC_PASSWORD"
echo "  Logs             : /workspace/logs/"
echo ""
echo "  To check status:"
echo "    supervisorctl status"
echo "    python phantom/browser_server.py status"
echo "    python phantom/session_health.py status"
echo ""
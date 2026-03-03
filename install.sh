#!/usr/bin/env bash
# install.sh — Setup script for Phantom browser automation agent
# Installs Python dependencies, Psiphon proxy, VNC resilience, and supervisord configs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHANTOM_DIR="$SCRIPT_DIR/phantom"

echo "=== Phantom Browser Automation — Install ==="
echo ""

# --- 1. Python dependencies ------------------------------------------------
echo "▶ Installing Python dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "  ✓ Python packages installed"

# --- 2. Playwright browsers ------------------------------------------------
echo "▶ Installing Playwright browsers..."
python -m playwright install chromium 2>/dev/null || true
echo "  ✓ Playwright browsers installed"


# --- 3. Psiphon tunnel core (proxy) ----------------------------------------
PSIPHON_BIN="$PHANTOM_DIR/psiphon-tunnel-core"
if [ -f "$PSIPHON_BIN" ] && [ -x "$PSIPHON_BIN" ]; then
    echo "▶ Psiphon binary already exists, skipping download"
else
    echo "▶ Downloading Psiphon tunnel core..."
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)  PSIPHON_URL="https://github.com/Psiphon-Labs/psiphon-tunnel-core-binaries/raw/master/linux/psiphon-tunnel-core-x86_64" ;;
        aarch64) PSIPHON_URL="https://github.com/Psiphon-Labs/psiphon-tunnel-core-binaries/raw/master/linux/psiphon-tunnel-core-arm64" ;;
        *)       echo "  ✗ Unsupported architecture: $ARCH"; exit 1 ;;
    esac
    curl -L -o "$PSIPHON_BIN" "$PSIPHON_URL"
    chmod +x "$PSIPHON_BIN"
    echo "  ✓ Psiphon binary downloaded ($ARCH)"
fi

# Create Psiphon data directory
mkdir -p "$PHANTOM_DIR/psiphon_data"
echo "  ✓ Psiphon data directory ready"

# --- 4. VNC resilience -----------------------------------------------------
VNC_DIR="$SCRIPT_DIR/vnc"
if [ -d "/opt/novnc" ] && [ -d "$VNC_DIR" ]; then
    echo "▶ Setting up VNC resilience..."

    # Copy resilient VNC page to noVNC web root
    cp "$VNC_DIR/vnc_resilient.html" /opt/novnc/vnc_auto.html

    # Install nginx WebSocket proxy config for VNC
    if [ -d "/etc/nginx/conf.d" ]; then
        cp "$VNC_DIR/nginx_vnc.conf" /etc/nginx/conf.d/vnc.conf
        nginx -t 2>/dev/null && nginx -s reload 2>/dev/null || true
        echo "  ✓ VNC nginx proxy on port 6081"
    fi

    echo "  ✓ Resilient VNC page installed (vnc_auto.html)"
else
    echo "  ⚠ noVNC or vnc dir not found, skipping VNC resilience setup"
fi

# --- 5. Supervisord configs ------------------------------------------------
SUPERVISOR_DIR="/etc/supervisor/conf.d"
if [ -d "$SUPERVISOR_DIR" ]; then
    echo "▶ Installing supervisord configs..."

    # Psiphon proxy
    cat > "$SUPERVISOR_DIR/psiphon.conf" << EOF
[program:psiphon]
command=$PSIPHON_BIN -config $PHANTOM_DIR/psiphon.config.json
directory=$PHANTOM_DIR
user=root
autostart=true
autorestart=true
startsecs=5
startretries=10
stderr_logfile=/var/log/supervisor/psiphon.err.log
stdout_logfile=/var/log/supervisor/psiphon.out.log
stdout_logfile_maxbytes=1MB
stderr_logfile_maxbytes=1MB
EOF

    # Browser server
    cat > "$SUPERVISOR_DIR/browser_server.conf" << EOF
[program:phantom_browser]
command=python $PHANTOM_DIR/browser_server.py start --foreground
directory=$SCRIPT_DIR
user=root
autostart=true
autorestart=true
startsecs=5
startretries=5
stderr_logfile=/var/log/supervisor/phantom_browser.err.log
stdout_logfile=/var/log/supervisor/phantom_browser.out.log
stdout_logfile_maxbytes=1MB
stderr_logfile_maxbytes=1MB
EOF

    supervisorctl reread 2>/dev/null || true
    supervisorctl update 2>/dev/null || true
    echo "  ✓ Supervisord configs installed"
else
    echo "  ⚠ Supervisord not found, skipping config installation"
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Services:"
echo "  • Psiphon proxy:  localhost:18080 (HTTP) / localhost:18081 (SOCKS)"
echo "  • Browser:        localhost:9222 (CDP)"
echo "  • VNC (direct):   localhost:6080/vnc_auto.html"
echo "  • VNC (proxied):  localhost:6081/vnc_auto.html"
echo ""
echo "Start services:  supervisorctl start psiphon phantom_browser"
echo "Check status:    supervisorctl status"
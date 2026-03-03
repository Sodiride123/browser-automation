#!/usr/bin/env bash
# install.sh — Setup script for Phantom browser automation agent
# Installs Python deps, Playwright, Psiphon proxy, and supervisord services.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHANTOM_DIR="$SCRIPT_DIR/phantom"
SUPERVISOR_SRC="$SCRIPT_DIR/supervisor/supervisord.conf"

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

# --- 4. Supervisord setup --------------------------------------------------
echo "▶ Setting up supervisord services..."

SUPERVISOR_CONF_DIR="/etc/supervisor/conf.d"
if [ -d "$SUPERVISOR_CONF_DIR" ] && [ -f "$SUPERVISOR_SRC" ]; then
    # Remove old individual configs (replaced by unified phantom.conf)
    rm -f "$SUPERVISOR_CONF_DIR/_superninja_startup.conf"
    rm -f "$SUPERVISOR_CONF_DIR/agent-dashboard.conf"
    rm -f "$SUPERVISOR_CONF_DIR/browser_server.conf"
    rm -f "$SUPERVISOR_CONF_DIR/psiphon.conf"

    # Install unified config
    cp "$SUPERVISOR_SRC" "$SUPERVISOR_CONF_DIR/phantom.conf"
    echo "  ✓ Installed phantom.conf to $SUPERVISOR_CONF_DIR"

    # Ensure main supervisord.conf includes conf.d
    MAIN_CONF="/etc/supervisor/supervisord.conf"
    if ! grep -q "include" "$MAIN_CONF" 2>/dev/null; then
        cat > "$MAIN_CONF" << 'EOF'
[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisord]
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
childlogdir=/var/log/supervisor

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[include]
files = /etc/supervisor/conf.d/*.conf
EOF
        echo "  ✓ Updated main supervisord.conf"
    fi

    # Reload supervisord
    supervisorctl reread 2>/dev/null || true
    supervisorctl update 2>/dev/null || true
    echo "  ✓ Supervisord reloaded"
else
    echo "  ⚠ Supervisord not found or config missing, skipping"
fi

# --- 5. Patch platform browser_api.py to use CDP --------------------------
echo "▶ Patching platform browser_api.py to use CDP..."
BROWSER_API="/app/browser_api.py"
if [ -f "$BROWSER_API" ]; then
    if grep -q "connect_over_cdp" "$BROWSER_API" 2>/dev/null; then
        echo "  ✓ browser_api.py already patched"
    else
        # Backup original
        cp "$BROWSER_API" "$BROWSER_API.bak"
        # Apply patch using Python for reliability
        python3 << 'PYEOF'
import re

with open("/app/browser_api.py", "r") as f:
    content = f.read()

old_startup = '''    async def startup(self):
        """Initialize the browser instance on startup"""
        try:
            print("Starting browser initialization...")
            playwright = await async_playwright().start()
            print("Playwright started, launching browser...")

            # Use non-headless mode for testing with slower timeouts
            launch_options = {"headless": False, "timeout": 60000}

            try:
                self.browser = await playwright.chromium.launch(**launch_options)
                print("Browser launched successfully")
            except Exception as browser_error:
                print(f"Failed to launch browser: {browser_error}")
                # Try with minimal options
                print("Retrying with minimal options...")
                launch_options = {"timeout": 90000}
                self.browser = await playwright.chromium.launch(**launch_options)
                print("Browser launched with minimal options")

            try:
                await self.get_current_page()
                print("Found existing page, using it")
            except Exception as page_error:
                print(f"Error finding existing page, creating new one. ( {page_error})")
                page = await self.browser.new_page()
                print("New page created successfully")
                self.pages.append(page)
                # Navigate to about:blank to ensure page is ready
                # await page.goto("google.com", timeout=30000)
                # print("Navigated to google.com")

            self.current_page_index = len(self.pages) - 1
            print("Browser initialization completed successfully")
        except Exception as e:
            print(f"Browser startup error: {str(e)}")
            traceback.print_exc()
            raise RuntimeError(f"Browser initialization failed: {str(e)}")'''

new_startup = '''    async def startup(self):
        """Initialize the browser instance on startup.

        Connects to the persistent browser via CDP (port 9222) instead of
        launching a new one.  This shares the same browser_data profile,
        proxy, stealth flags, and login sessions managed by browser_server.
        Falls back to launching a standalone browser if CDP is unavailable.
        """
        CDP_ENDPOINT = os.environ.get("CDP_ENDPOINT", "http://localhost:9222")
        try:
            print(f"Connecting to persistent browser at {CDP_ENDPOINT} ...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
            print("Connected to persistent browser via CDP")

            # Reuse existing contexts/pages
            contexts = self.browser.contexts
            if contexts:
                for ctx in contexts:
                    self.pages.extend(ctx.pages)
                if self.pages:
                    print(f"Found {len(self.pages)} existing page(s)")
                else:
                    page = await contexts[0].new_page()
                    self.pages.append(page)
                    print("Created new page in existing context")
            else:
                ctx = await self.browser.new_context()
                page = await ctx.new_page()
                self.pages.append(page)
                print("Created new context and page")

            self.current_page_index = len(self.pages) - 1
            print("Browser initialization completed successfully (CDP)")
        except Exception as cdp_err:
            print(f"CDP connection failed ({cdp_err}), falling back to standalone launch...")
            try:
                playwright = await async_playwright().start()
                launch_options = {"headless": False, "timeout": 60000}
                self.browser = await playwright.chromium.launch(**launch_options)
                print("Standalone browser launched")
                try:
                    await self.get_current_page()
                    print("Found existing page, using it")
                except Exception:
                    page = await self.browser.new_page()
                    self.pages.append(page)
                    print("New page created")
                self.current_page_index = len(self.pages) - 1
                print("Browser initialization completed (standalone fallback)")
            except Exception as e:
                print(f"Browser startup error: {str(e)}")
                traceback.print_exc()
                raise RuntimeError(f"Browser initialization failed: {str(e)}")'''

if old_startup in content:
    content = content.replace(old_startup, new_startup)
    with open("/app/browser_api.py", "w") as f:
        f.write(content)
    print("  ✓ browser_api.py patched (CDP connection)")
else:
    print("  ⚠ Could not find expected startup code — may already be patched or changed")
PYEOF
    fi
else
    echo "  ⚠ /app/browser_api.py not found, skipping patch"
fi

# --- 6. Create log directory -----------------------------------------------
mkdir -p /workspace/logs
echo "  ✓ Log directory ready"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Services (managed by supervisord):"
echo "  • Xvfb:          display :99"
echo "  • x11vnc:        port 5901 (no password)"
echo "  • noVNC:         port 6081 (websockify direct, no nginx)"
echo "  • Browser:       port 9222 (CDP, browser_data profile, psiphon proxy)"
echo "  • Psiphon:       port 18080 (HTTP proxy) / 18081 (SOCKS)"
echo "  • Dashboard:     port 9000"
echo ""
echo "Commands:"
echo "  supervisorctl status              # Check all services"
echo "  supervisorctl restart all          # Restart everything"
echo "  python phantom/browser_server.py status  # Browser details"
echo "  python phantom/session_health.py status  # Login sessions"
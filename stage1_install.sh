#!/usr/bin/env bash
# =============================================================================
# STAGE 1 — Dependency Installation Script
# =============================================================================
# Purpose: Install ALL dependencies into a clean SuperNinja sandbox to create
#          a reusable VM image. Run this ONCE to bake the image.
#
# What this does:
#   1. Installs system packages (curl, git, supervisor, x11vnc, novnc, etc.)
#   2. Installs Python dependencies from requirements.txt
#   3. Installs Playwright + Chromium browser
#   4. Downloads Psiphon proxy binary
#   5. Installs supervisord config (services: browser, VNC, dashboard, proxy)
#   6. Patches /app/browser_api.py to use CDP (shared persistent browser)
#   7. Fixes /root/s3_config.json trailing comma bug
#   8. Creates required directories
#   9. Verifies all components are ready
#
# Usage:
#   chmod +x stage1_install.sh
#   ./stage1_install.sh
#
# After this script completes, snapshot/save the VM image.
# Users with this image can then run stage2_start.sh to launch the app.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHANTOM_DIR="$SCRIPT_DIR/phantom"
SUPERVISOR_SRC="$SCRIPT_DIR/supervisor/supervisord.conf"

echo ""
echo "============================================================"
echo "  Phantom Browser Automation — Stage 1: Dependency Install"
echo "============================================================"
echo ""

# --- 1. System packages -------------------------------------------------------
echo "▶ [1/9] Checking system packages..."

MISSING_PKGS=()
for pkg in curl git supervisor x11vnc python3-pip; do
    if ! dpkg -s "$pkg" &>/dev/null; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo "  Installing missing packages: ${MISSING_PKGS[*]}"
    apt-get update -qq
    apt-get install -y -qq "${MISSING_PKGS[@]}"
else
    echo "  ✓ All required system packages already installed"
fi

# noVNC (websockify)
if ! python3 -c "import websockify" &>/dev/null; then
    echo "  Installing websockify for noVNC..."
    pip install -q websockify
fi

if [ ! -d /opt/novnc ]; then
    echo "  Installing noVNC..."
    git clone --depth=1 https://github.com/novnc/noVNC.git /opt/novnc 2>/dev/null || true
else
    echo "  ✓ noVNC already installed at /opt/novnc"
fi

echo "  ✓ System packages ready"

# --- 2. Python dependencies ---------------------------------------------------
echo "▶ [2/9] Installing Python dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "  ✓ Python packages installed"

# --- 3. Playwright + Chromium -------------------------------------------------
echo "▶ [3/9] Installing Playwright browsers..."
python -m playwright install chromium 2>/dev/null || true
python -m playwright install-deps chromium 2>/dev/null || true
echo "  ✓ Playwright + Chromium installed"

# --- 4. Psiphon proxy binary --------------------------------------------------
echo "▶ [4/9] Setting up Psiphon proxy..."
PSIPHON_BIN="$PHANTOM_DIR/psiphon-tunnel-core"
if [ -f "$PSIPHON_BIN" ] && [ -x "$PSIPHON_BIN" ]; then
    echo "  ✓ Psiphon binary already present"
else
    echo "  Downloading Psiphon tunnel core..."
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)  PSIPHON_URL="https://github.com/Psiphon-Labs/psiphon-tunnel-core-binaries/raw/master/linux/psiphon-tunnel-core-x86_64" ;;
        aarch64) PSIPHON_URL="https://github.com/Psiphon-Labs/psiphon-tunnel-core-binaries/raw/master/linux/psiphon-tunnel-core-arm64" ;;
        *)       echo "  ⚠ Unsupported architecture: $ARCH — skipping Psiphon"; PSIPHON_URL="" ;;
    esac
    if [ -n "$PSIPHON_URL" ]; then
        curl -sL -o "$PSIPHON_BIN" "$PSIPHON_URL"
        chmod +x "$PSIPHON_BIN"
        echo "  ✓ Psiphon binary downloaded ($ARCH)"
    fi
fi
mkdir -p "$PHANTOM_DIR/psiphon_data"
echo "  ✓ Psiphon ready"

# --- 5. Supervisord config ----------------------------------------------------
echo "▶ [5/9] Installing supervisord services config..."
SUPERVISOR_CONF_DIR="/etc/supervisor/conf.d"

if [ -d "$SUPERVISOR_CONF_DIR" ] && [ -f "$SUPERVISOR_SRC" ]; then
    # Remove old individual configs replaced by unified phantom.conf
    rm -f "$SUPERVISOR_CONF_DIR/_superninja_startup.conf"
    rm -f "$SUPERVISOR_CONF_DIR/agent-dashboard.conf"
    rm -f "$SUPERVISOR_CONF_DIR/browser_server.conf"
    rm -f "$SUPERVISOR_CONF_DIR/psiphon.conf"

    # Install unified config
    cp "$SUPERVISOR_SRC" "$SUPERVISOR_CONF_DIR/phantom.conf"
    echo "  ✓ Installed phantom.conf → $SUPERVISOR_CONF_DIR"

    # Disable browser_api in the platform's supervisord.conf (if present).
    # Phantom uses its own persistent browser (phantom_browser on port 9222),
    # so the platform's browser_api would launch a duplicate Chromium window.
    PLATFORM_CONF="$SUPERVISOR_CONF_DIR/supervisord.conf"
    if [ -f "$PLATFORM_CONF" ] && grep -q "\[program:browser_api\]" "$PLATFORM_CONF" 2>/dev/null; then
        if ! grep -A1 "\[program:browser_api\]" "$PLATFORM_CONF" | grep -q "autostart=false"; then
            sed -i '/\[program:browser_api\]/a autostart=false\nautorestart=false' "$PLATFORM_CONF"
            echo "  ✓ Disabled browser_api in platform supervisord.conf"
        else
            echo "  ✓ browser_api already disabled in platform supervisord.conf"
        fi
    fi

    # Ensure main supervisord.conf has [include] section
    MAIN_CONF="/etc/supervisor/supervisord.conf"
    if ! grep -q "\[include\]" "$MAIN_CONF" 2>/dev/null; then
        cat >> "$MAIN_CONF" << 'EOF'

[include]
files = /etc/supervisor/conf.d/*.conf
EOF
        echo "  ✓ Added [include] to main supervisord.conf"
    fi

    supervisorctl reread 2>/dev/null || true
    supervisorctl update 2>/dev/null || true
    echo "  ✓ Supervisord reloaded"
else
    echo "  ⚠ Supervisord conf.d not found or supervisor/supervisord.conf missing — skipping"
fi

# --- 6. Patch /app/browser_api.py to use CDP ----------------------------------
echo "▶ [6/9] Patching platform browser_api.py to use CDP..."
BROWSER_API="/app/browser_api.py"
if [ -f "$BROWSER_API" ]; then
    if grep -q "connect_over_cdp" "$BROWSER_API" 2>/dev/null; then
        echo "  ✓ browser_api.py already patched (CDP)"
    else
        cp "$BROWSER_API" "${BROWSER_API}.bak"
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

            self.current_page_index = len(self.pages) - 1
            print("Browser initialization completed successfully")
        except Exception as e:
            print(f"Browser startup error: {str(e)}")
            traceback.print_exc()
            raise RuntimeError(f"Browser initialization failed: {str(e)}")'''

new_startup = '''    async def startup(self):
        """Initialize the browser instance on startup.

        Connects to the persistent browser via CDP (port 9222) instead of
        launching a new one. This shares the same browser_data profile,
        proxy, stealth flags, and login sessions managed by browser_server.
        Falls back to launching a standalone browser if CDP is unavailable.
        """
        CDP_ENDPOINT = os.environ.get("CDP_ENDPOINT", "http://localhost:9222")
        try:
            print(f"Connecting to persistent browser at {CDP_ENDPOINT} ...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
            print("Connected to persistent browser via CDP")

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
    print("  ⚠ Could not find expected startup code — may already be patched or changed upstream")
PYEOF
    fi
else
    echo "  ⚠ /app/browser_api.py not found — skipping patch"
fi

# --- 7. Fix /root/s3_config.json trailing comma bug ---------------------------
echo "▶ [7/9] Fixing /root/s3_config.json (trailing comma bug)..."
S3_CONFIG="/root/s3_config.json"
if [ -f "$S3_CONFIG" ]; then
    # Use Python to validate and fix trailing commas in JSON
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
    print("  ✓ s3_config.json is valid JSON (fixed if needed)")
except json.JSONDecodeError as e:
    print(f"  ⚠ Could not auto-fix s3_config.json: {e}")
    sys.exit(0)  # non-fatal
PYEOF
else
    echo "  ⚠ /root/s3_config.json not found — will be created at runtime from /dev/shm/mcp-token"
fi

# --- 8. Create required directories -------------------------------------------
echo "▶ [8/9] Creating required directories..."
mkdir -p /workspace/logs
mkdir -p "$SCRIPT_DIR/phantom/screenshots"
mkdir -p "$SCRIPT_DIR/phantom/browser_data"
mkdir -p "$SCRIPT_DIR/phantom/psiphon_data"
mkdir -p "$SCRIPT_DIR/reports"
mkdir -p "$SCRIPT_DIR/memory"
echo "  ✓ Directories created"

# --- 9. Verify installation ---------------------------------------------------
echo "▶ [9/9] Verifying installation..."

ERRORS=0

# Check Python packages
for pkg in playwright flask flask_cors requests boto3 mcp; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo "  ✓ Python: $pkg"
    else
        echo "  ✗ Python: $pkg MISSING"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check Playwright Chromium
if python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.stop()" 2>/dev/null; then
    echo "  ✓ Playwright: OK"
else
    echo "  ⚠ Playwright: could not verify (may still work)"
fi

# Check Psiphon binary
if [ -f "$PSIPHON_BIN" ] && [ -x "$PSIPHON_BIN" ]; then
    echo "  ✓ Psiphon: binary present"
else
    echo "  ⚠ Psiphon: binary missing (proxy will be unavailable)"
fi

# Check supervisord config
if [ -f "/etc/supervisor/conf.d/phantom.conf" ]; then
    echo "  ✓ Supervisord: phantom.conf installed"
else
    echo "  ⚠ Supervisord: phantom.conf not installed"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "============================================================"
    echo "  ✅ Stage 1 Complete — All dependencies installed!"
    echo "============================================================"
    echo ""
    echo "  Next steps:"
    echo "  1. Snapshot/save this VM image"
    echo "  2. Users with this image run: ./stage2_start.sh"
    echo ""
else
    echo "============================================================"
    echo "  ⚠ Stage 1 Complete with $ERRORS warning(s) — review above"
    echo "============================================================"
fi
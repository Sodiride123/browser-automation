#!/usr/bin/env python3
"""
Stealth patches for Chromium anti-bot detection evasion.

This module provides the stealth JavaScript that gets injected into every page
via Playwright's context.add_init_script(). It's automatically applied when
connecting to the browser via BrowserInterface.connect_cdp() or start().

Usage:
    # Automatic (preferred) — stealth is applied by BrowserInterface:
    from browser_interface import BrowserInterface
    browser = BrowserInterface.connect_cdp()  # stealth already active

    # Manual — get the script for custom use:
    from phantom.stealth import STEALTH_JS
    browser.context.add_init_script(STEALTH_JS)

    # Check stealth status on current page:
    from phantom.stealth import check_stealth
    result = check_stealth(browser)

    # CLI:
    python phantom/stealth.py check   # Verify stealth via running browser
"""

# ─── Stealth JavaScript ──────────────────────────────────────────────────────
# Combined script injected via context.add_init_script().
# Runs before any page JavaScript on every navigation and new tab.

STEALTH_JS = """
// === Phantom Stealth Patches ===
// Injected via Playwright context.add_init_script()
// Runs before any page JS on every navigation.

// 1. Hide navigator.webdriver (Google's primary bot check)
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
});

// 2. Fix chrome.runtime (normal Chrome has this, automated often doesn't)
if (!window.chrome) {
    window.chrome = {};
}
if (!window.chrome.runtime) {
    window.chrome.runtime = {
        connect: function() {},
        sendMessage: function() {},
        onMessage: { addListener: function() {} },
    };
}

// 3. Fix permissions API (automated browsers return inconsistent states)
(function() {
    try {
        const originalQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission });
            }
            return originalQuery(parameters);
        };
    } catch(e) {}
})();

// 4. Fix plugins array (automated Chrome often has empty plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer',
              description: 'Portable Document Format',
              length: 1, item: function(i) { return this; },
              namedItem: function(n) { return this; },
              0: { type: 'application/x-google-chrome-pdf',
                   suffixes: 'pdf', description: 'Portable Document Format',
                   enabledPlugin: null }},
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
              description: '', length: 1,
              item: function(i) { return this; },
              namedItem: function(n) { return this; },
              0: { type: 'application/pdf', suffixes: 'pdf',
                   description: '', enabledPlugin: null }},
            { name: 'Native Client', filename: 'internal-nacl-plugin',
              description: '', length: 2,
              item: function(i) { return this; },
              namedItem: function(n) { return this; },
              0: { type: 'application/x-nacl', suffixes: '',
                   description: 'Native Client Executable', enabledPlugin: null },
              1: { type: 'application/x-pnacl', suffixes: '',
                   description: 'Portable Native Client Executable',
                   enabledPlugin: null }},
        ];
        plugins.length = 3;
        plugins.item = function(i) { return this[i] || null; };
        plugins.namedItem = function(n) {
            for (let i = 0; i < this.length; i++) {
                if (this[i].name === n) return this[i];
            }
            return null;
        };
        plugins.refresh = function() {};
        return plugins;
    },
    configurable: true,
});

// 5. Fix languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true,
});

// 6. Remove automation artifacts
(function() {
    try {
        const props = Object.getOwnPropertyNames(document);
        for (const prop of props) {
            if (prop.match(/^cdc_/)) {
                delete document[prop];
            }
        }
        delete navigator.__proto__.__webdriver_evaluate;
        delete navigator.__proto__.__driver_evaluate;
        delete navigator.__proto__.__webdriver_unwrap;
        delete navigator.__proto__.__driver_unwrap;
        delete navigator.__proto__.__selenium_evaluate;
        delete navigator.__proto__.__fxdriver_evaluate;
    } catch(e) {}
})();

// 7. Fix WebGL vendor/renderer
(function() {
    try {
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Google Inc. (NVIDIA)';
            if (parameter === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Direct3D11 vs_5_0 ps_5_0, D3D11)';
            return getParameter.call(this, parameter);
        };
        if (typeof WebGL2RenderingContext !== 'undefined') {
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Google Inc. (NVIDIA)';
                if (parameter === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return getParameter2.call(this, parameter);
            };
        }
    } catch(e) {}
})();
"""

# JS snippet to check stealth status (returns JSON)
STEALTH_CHECK_JS = """() => {
    return JSON.stringify({
        webdriver: navigator.webdriver,
        webdriverType: typeof navigator.webdriver,
        chromeRuntime: !!window.chrome?.runtime,
        plugins: navigator.plugins.length,
        languages: navigator.languages,
    });
}"""


def check_stealth(browser) -> dict:
    """Check if stealth patches are active on the current page.

    Args:
        browser: A BrowserInterface instance (connected).

    Returns:
        dict with detection test results:
        - webdriver: value of navigator.webdriver (should be None/undefined)
        - webdriverType: typeof navigator.webdriver (should be "undefined")
        - chromeRuntime: bool (should be True)
        - plugins: int (should be > 0)
        - languages: list (should be ['en-US', 'en'])
    """
    import json
    try:
        raw = browser.evaluate(STEALTH_CHECK_JS)
        result = json.loads(raw)
        return result
    except Exception as e:
        return {"error": str(e)}


def print_stealth_status(result: dict):
    """Pretty-print stealth check results."""
    if "error" in result:
        print(f"  ❌ Stealth check error: {result['error']}")
        return False

    all_good = True

    wd = result.get("webdriver")
    wd_type = result.get("webdriverType")
    if wd is None or wd is False or wd_type == "undefined":
        print("  ✅ navigator.webdriver is hidden")
    else:
        print(f"  ❌ navigator.webdriver = {wd} (DETECTABLE)")
        all_good = False

    if result.get("chromeRuntime"):
        print("  ✅ chrome.runtime is present")
    else:
        print("  ⚠️  chrome.runtime is missing")
        all_good = False

    plugins = result.get("plugins", 0)
    if plugins > 0:
        print(f"  ✅ navigator.plugins has {plugins} entries")
    else:
        print("  ⚠️  navigator.plugins is empty")
        all_good = False

    return all_good


def main():
    """CLI entry point — check stealth on the running browser."""
    import sys
    from pathlib import Path
    # Ensure parent dir is on path for browser_interface import
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from browser_interface import BrowserInterface

    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"

    if cmd == "check":
        print("🔍 Checking stealth status on running browser...")
        try:
            browser = BrowserInterface.connect_cdp()
            result = check_stealth(browser)
            print_stealth_status(result)
            browser.stop()
        except ConnectionError:
            print("  ❌ No browser running. Start with: python phantom/browser_server.py start")
            sys.exit(1)
    else:
        print(f"Usage: python phantom/stealth.py check")
        sys.exit(1)


if __name__ == "__main__":
    main()
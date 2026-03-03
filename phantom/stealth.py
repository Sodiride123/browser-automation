#!/usr/bin/env python3
"""
Stealth patches for Chromium anti-bot detection evasion.

Injects JavaScript via CDP (Page.addScriptToEvaluateOnNewDocument) to hide
automation fingerprints. Applied automatically on every new page/tab.

Usage:
    from phantom.stealth import apply_stealth, apply_stealth_to_all_pages

    # Apply to a single CDP target (websocket URL)
    apply_stealth("ws://localhost:9222/devtools/page/ABC123")

    # Apply to all open pages
    apply_stealth_to_all_pages()
"""

import json
import os
import subprocess
import tempfile
import urllib.request
from typing import Optional

CDP_ENDPOINT = "http://localhost:9222"

# ─── Stealth JavaScript Patches ───────────────────────────────────────────────
# Each patch targets a specific detection vector used by Google and other
# anti-bot systems. Combined, they make the browser appear as a normal
# user-controlled Chrome instance.

STEALTH_SCRIPTS = [
    # 1. Hide navigator.webdriver
    # Google's primary check — if true, login is blocked immediately.
    """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true,
    });
    """,

    # 2. Fix chrome.runtime
    # Normal Chrome has window.chrome with runtime object.
    # Automated Chrome often has it missing or incomplete.
    """
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
    """,

    # 3. Fix permissions API
    # Automated browsers return inconsistent permission states.
    """
    (function() {
        const originalQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission });
            }
            return originalQuery(parameters);
        };
    })();
    """,

    # 4. Fix plugins array
    # Normal Chrome reports plugins; automated Chrome often has empty array.
    """
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
    """,

    # 5. Fix languages
    # Ensure navigator.languages returns a realistic value.
    """
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
        configurable: true,
    });
    """,

    # 6. Hide automation-related properties from window
    # Some detection scripts check for these CDP artifacts.
    """
    (function() {
        // Remove cdc_ properties (ChromeDriver artifacts)
        const props = Object.getOwnPropertyNames(document);
        for (const prop of props) {
            if (prop.match(/^cdc_/)) {
                delete document[prop];
            }
        }

        // Remove __webdriver properties
        delete navigator.__proto__.__webdriver_evaluate;
        delete navigator.__proto__.__driver_evaluate;
        delete navigator.__proto__.__webdriver_unwrap;
        delete navigator.__proto__.__driver_unwrap;
        delete navigator.__proto__.__selenium_evaluate;
        delete navigator.__proto__.__fxdriver_evaluate;
        delete navigator.__proto__.__driver_unwrap;
    })();
    """,

    # 7. Fix WebGL vendor/renderer
    # Headless or automated Chrome may report different WebGL strings.
    """
    (function() {
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {
                return 'Google Inc. (NVIDIA)';
            }
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {
                return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Direct3D11 vs_5_0 ps_5_0, D3D11)';
            }
            return getParameter.call(this, parameter);
        };

        // Also patch WebGL2
        if (typeof WebGL2RenderingContext !== 'undefined') {
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Google Inc. (NVIDIA)';
                if (parameter === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return getParameter2.call(this, parameter);
            };
        }
    })();
    """,

    # 8. Fix iframe contentWindow detection
    # Some anti-bot scripts create iframes and check if contentWindow
    # has automation artifacts.
    """
    (function() {
        const originalAttachShadow = Element.prototype.attachShadow;
        Element.prototype.attachShadow = function() {
            return originalAttachShadow.apply(this, arguments);
        };
    })();
    """,
]

# Combined script for single injection
STEALTH_COMBINED = "\n".join(
    f"// Stealth patch {i+1}\n(function(){{{script}}})();"
    for i, script in enumerate(STEALTH_SCRIPTS)
)


def _cdp_send(ws_url: str, method: str, params: Optional[dict] = None) -> dict:
    """Send a CDP command via HTTP (using the /json/protocol endpoint).

    For addScriptToEvaluateOnNewDocument we use the HTTP-based CDP endpoint
    since it doesn't require a WebSocket library.
    """
    import http.client
    import json as _json

    # Extract target ID from ws URL: ws://localhost:9222/devtools/page/TARGET_ID
    target_id = ws_url.rsplit("/", 1)[-1]

    # Use the /json/send endpoint (not available in all Chrome versions)
    # Instead, we'll use a simple approach: connect via HTTP and use
    # the Target.sendMessageToTarget approach

    # Actually, the simplest approach for our use case is to use
    # subprocess to call a small Node.js script or use Python websockets.
    # But to keep dependencies minimal, let's use the /json/protocol approach.

    # For Page.addScriptToEvaluateOnNewDocument, we need WebSocket.
    # Let's use Python's built-in approach.
    raise NotImplementedError("Use apply_stealth() instead")


def get_all_targets() -> list[dict]:
    """Get all CDP targets (pages/tabs)."""
    try:
        resp = urllib.request.urlopen(f"{CDP_ENDPOINT}/json/list", timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        print(f"Failed to get CDP targets: {e}")
        return []


def apply_stealth_via_node(target_ws_url: Optional[str] = None) -> bool:
    """Apply stealth patches to a CDP target using a Node.js helper.

    If target_ws_url is None, applies to all open pages.
    Returns True if successful.
    """

    targets = []
    if target_ws_url:
        targets = [target_ws_url]
    else:
        pages = get_all_targets()
        targets = [p["webSocketDebuggerUrl"] for p in pages
                    if p.get("type") == "page" and "webSocketDebuggerUrl" in p]

    if not targets:
        print("No targets found to apply stealth patches")
        return False

    # Write stealth script to a temp file so Node can read it cleanly
    with tempfile.NamedTemporaryFile(mode='w', suffix='.stealth.js', delete=False) as sf:
        sf.write(STEALTH_COMBINED)
        stealth_path = sf.name

    # Create a Node.js script that connects via WebSocket and injects stealth
    node_script = (
        "const WebSocket = require('ws');\n"
        "const fs = require('fs');\n"
        "\n"
        "const STEALTH_SCRIPT = fs.readFileSync(process.argv[2], 'utf8');\n"
        "const targets = JSON.parse(process.argv[3]);\n"
        "\n"
        "async function applyToTarget(wsUrl) {\n"
        "    return new Promise((resolve, reject) => {\n"
        "        const ws = new WebSocket(wsUrl);\n"
        "        let msgId = 1;\n"
        "\n"
        "        ws.on('open', () => {\n"
        "            ws.send(JSON.stringify({\n"
        "                id: msgId++,\n"
        "                method: 'Page.addScriptToEvaluateOnNewDocument',\n"
        "                params: { source: STEALTH_SCRIPT }\n"
        "            }));\n"
        "\n"
        "            ws.send(JSON.stringify({\n"
        "                id: msgId++,\n"
        "                method: 'Runtime.evaluate',\n"
        "                params: {\n"
        "                    expression: STEALTH_SCRIPT,\n"
        "                    returnByValue: false\n"
        "                }\n"
        "            }));\n"
        "        });\n"
        "\n"
        "        let responses = 0;\n"
        "        ws.on('message', (data) => {\n"
        "            responses++;\n"
        "            if (responses >= 2) {\n"
        "                ws.close();\n"
        "                resolve(true);\n"
        "            }\n"
        "        });\n"
        "\n"
        "        ws.on('error', (err) => {\n"
        "            reject(err);\n"
        "        });\n"
        "\n"
        "        setTimeout(() => {\n"
        "            ws.close();\n"
        "            reject(new Error('Timeout'));\n"
        "        }, 10000);\n"
        "    });\n"
        "}\n"
        "\n"
        "async function main() {\n"
        "    for (const target of targets) {\n"
        "        try {\n"
        "            await applyToTarget(target);\n"
        "            console.log('OK: ' + target);\n"
        "        } catch (e) {\n"
        "            console.error('FAIL: ' + target + ' - ' + e.message);\n"
        "        }\n"
        "    }\n"
        "}\n"
        "\n"
        "main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });\n"
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(node_script)
        script_path = f.name

    try:
        env = os.environ.copy()
        env["NODE_PATH"] = "/usr/lib/node_modules"
        result = subprocess.run(
            ["node", script_path, stealth_path, json.dumps(targets)],
            capture_output=True, text=True, timeout=30, env=env
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"  ✅ Stealth applied: {line}")
            return True
        else:
            print(f"  ❌ Stealth injection failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("  ❌ Stealth injection timed out")
        return False
    except FileNotFoundError:
        print("  ❌ Node.js not found — cannot inject stealth patches")
        return False
    finally:
        os.unlink(script_path)
        os.unlink(stealth_path)


def apply_stealth_to_all_pages() -> int:
    """Apply stealth patches to all open browser pages.

    Returns the number of pages patched.
    """
    pages = get_all_targets()
    page_targets = [p for p in pages if p.get("type") == "page"]

    if not page_targets:
        print("No open pages found")
        return 0

    ws_urls = [p["webSocketDebuggerUrl"] for p in page_targets
               if "webSocketDebuggerUrl" in p]

    if apply_stealth_via_node():
        return len(ws_urls)
    return 0


def check_stealth(target_ws_url: Optional[str] = None) -> dict:
    """Check if stealth patches are active on a page.

    Returns a dict with detection test results.
    """

    if not target_ws_url:
        pages = get_all_targets()
        for p in pages:
            if p.get("type") == "page" and "webSocketDebuggerUrl" in p:
                target_ws_url = p["webSocketDebuggerUrl"]
                break

    if not target_ws_url:
        return {"error": "No page target found"}

    check_script = """
const WebSocket = require('ws');

async function check(wsUrl) {
    return new Promise((resolve, reject) => {
        const ws = new WebSocket(wsUrl);

        ws.on('open', () => {
            ws.send(JSON.stringify({
                id: 1,
                method: 'Runtime.evaluate',
                params: {
                    expression: `JSON.stringify({
                        webdriver: navigator.webdriver,
                        webdriverType: typeof navigator.webdriver,
                        chromeRuntime: !!window.chrome?.runtime,
                        plugins: navigator.plugins.length,
                        languages: navigator.languages,
                    })`,
                    returnByValue: true
                }
            }));
        });

        ws.on('message', (data) => {
            const msg = JSON.parse(data);
            if (msg.id === 1) {
                ws.close();
                try {
                    resolve(JSON.parse(msg.result.result.value));
                } catch(e) {
                    resolve(msg.result);
                }
            }
        });

        ws.on('error', reject);
        setTimeout(() => { ws.close(); reject(new Error('Timeout')); }, 10000);
    });
}

check(process.argv[2])
    .then(r => { console.log(JSON.stringify(r)); process.exit(0); })
    .catch(e => { console.error(e.message); process.exit(1); });
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(check_script)
        script_path = f.name

    try:
        env = os.environ.copy()
        env["NODE_PATH"] = "/usr/lib/node_modules"
        result = subprocess.run(
            ["node", script_path, target_ws_url],
            capture_output=True, text=True, timeout=15, env=env
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            return {"error": result.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}
    finally:
        os.unlink(script_path)


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python stealth.py [apply|check|status]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "apply":
        print("🥷 Applying stealth patches to all open pages...")
        count = apply_stealth_to_all_pages()
        print(f"   Patched {count} page(s)")

    elif cmd == "check":
        print("🔍 Checking stealth status...")
        result = check_stealth()
        print(json.dumps(result, indent=2))

        # Interpret results
        if "error" not in result:
            wd = result.get("webdriver")
            wd_type = result.get("webdriverType")
            if wd is None or wd is False or wd_type == "undefined":
                print("✅ navigator.webdriver is hidden")
            else:
                print(f"❌ navigator.webdriver = {wd} (DETECTABLE)")

            if result.get("chromeRuntime"):
                print("✅ chrome.runtime is present")
            else:
                print("⚠️  chrome.runtime is missing")

            plugins = result.get("plugins", 0)
            if plugins > 0:
                print(f"✅ navigator.plugins has {plugins} entries")
            else:
                print("⚠️  navigator.plugins is empty")

    elif cmd == "status":
        pages = get_all_targets()
        print(f"Browser has {len(pages)} target(s)")
        for p in pages:
            print(f"  [{p.get('type')}] {p.get('title', '')[:50]} — {p.get('url', '')[:60]}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
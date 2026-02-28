# Browser Automation Guide

## Overview

`browser_interface.py` provides **Playwright-based browser automation** for all agents. It wraps Chromium with a high-level Python API and CLI, and automatically captures **DevTools data** (console logs, JS errors, network failures) — making it ideal for end-to-end testing, visual verification, and debugging.

---

## Quick Start

### CLI Usage

```bash
# Navigate to a URL and see page info + error report
python browser_interface.py goto "https://example.com"

# Take a screenshot
python browser_interface.py screenshot page.png --url "https://example.com"

# Extract text from an element
python browser_interface.py text "h1" --url "https://example.com"

# Check a page for JS/console/network errors (exit code 1 if errors found)
python browser_interface.py check "http://0.0.0.0:3000"

# Show all console output from a page
python browser_interface.py console "http://0.0.0.0:3000"

# Save page as PDF
python browser_interface.py pdf report.pdf --url "https://example.com"

# Get page HTML
python browser_interface.py html --url "https://example.com" --selector "#main"
```

### Python API

```python
from browser_interface import BrowserInterface

with BrowserInterface() as b:
    b.goto("http://0.0.0.0:3000")
    print(b.title)
    b.screenshot("homepage.png")
    
    # Interact with the page
    b.fill("input#search", "hello world")
    b.click("button[type=submit]")
    b.wait_for("div.results")
    
    # Check for errors
    print(b.error_report())
    b.assert_no_errors()  # Raises AssertionError if any errors detected
```

---

## CLI Commands Reference

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `goto <url>` | Navigate and print page info + errors | `--wait`, `--headless` |
| `screenshot <path>` | Take screenshot | `--url`, `--full-page`, `--selector` |
| `text [selector]` | Extract visible text | `--url`, `--headless` |
| `html` | Get inner HTML | `--url`, `--selector` |
| `pdf <path>` | Save page as PDF | `--url`, `--format` |
| `check <url>` | **Error check** — report JS/console/network errors | `--wait`, `--headless` |
| `console <url>` | Show all console output | `--wait`, `--headless` |

### Global Flags

| Flag | Description |
|------|-------------|
| `--no-devtools` | Suppress the devtools error report |
| `--devtools-json` | Output devtools data as JSON (machine-readable) |

### Exit Codes

- `0` — No errors detected
- `1` — Errors found (JS errors, console errors, or network failures)

This makes it easy to use in scripts:
```bash
python browser_interface.py check "http://0.0.0.0:3000" || echo "ERRORS FOUND!"
```

---

## Python API Reference

### Initialization

```python
b = BrowserInterface(
    headless=False,        # False = visible on VNC, True = no display
    viewport_width=1280,   # Browser viewport width
    viewport_height=720,   # Browser viewport height
    timeout=30000,         # Default timeout in ms
    slow_mo=0,             # Delay between actions (useful for demos)
    capture_console=True,  # Auto-capture console/errors/network
)
```

### Navigation

```python
b.goto(url, wait_until="load")     # Navigate to URL
b.reload()                          # Reload page
b.go_back()                         # Navigate back
b.go_forward()                      # Navigate forward
```

`wait_until` options: `"load"`, `"domcontentloaded"`, `"networkidle"`, `"commit"`

### Page Properties

```python
b.title      # Page title
b.url        # Current URL
b.content    # Full page HTML
```

### Interaction

```python
b.click(selector)                        # Click element
b.double_click(selector)                 # Double-click
b.right_click(selector)                  # Right-click
b.hover(selector)                        # Hover over element
b.fill(selector, value)                  # Fill input (clears first)
b.type_text(selector, text, delay=50)    # Type character by character
b.press(selector, key)                   # Press key (Enter, Tab, Escape, etc.)
b.select_option(selector, value=..., label=..., index=...)  # Select dropdown
b.check(selector)                        # Check checkbox/radio
b.uncheck(selector)                      # Uncheck checkbox
```

Selectors can be CSS (`"button.submit"`), text-based (`"text=Submit"`), or any Playwright locator.

### Content Extraction

```python
b.text(selector)             # Visible text of element
b.html(selector)             # Inner HTML
b.attribute(selector, name)  # Get attribute (e.g., href, src)
b.query_all(selector)        # Count matching elements
b.query_texts(selector)      # Get text of ALL matching elements
b.evaluate(js)               # Execute arbitrary JavaScript
```

### Screenshots & PDF

```python
b.screenshot("page.png")                          # Basic screenshot
b.screenshot("full.png", full_page=True)           # Full scrollable page
b.screenshot("element.png", selector="#hero")      # Screenshot specific element
b.pdf("page.pdf", format="A4")                     # Save as PDF
```

### Waiting

```python
b.wait_for(selector, state="visible")    # Wait for element (visible/hidden/attached/detached)
b.wait_for_url(pattern)                  # Wait for URL to match
b.wait_for_load("networkidle")           # Wait for load state
b.sleep(seconds)                         # Simple sleep
```

### Scrolling

```python
b.scroll_down(px=500)       # Scroll down
b.scroll_up(px=500)         # Scroll up
b.scroll_to_top()           # Scroll to top
b.scroll_to_bottom()        # Scroll to bottom
b.scroll_to(selector)       # Scroll element into view
```

### Tabs

```python
b.new_tab(url)     # Open new tab
b.close_tab()      # Close current tab
b.tab_count        # Number of open tabs
```

### Cookies & Storage

```python
b.cookies()                                  # Get all cookies
b.set_cookie(name, value, url=...)          # Set cookie
b.clear_cookies()                            # Clear all cookies
b.local_storage()                            # Get all localStorage
b.local_storage("key")                       # Get specific key
```

### Network Control

```python
b.block_resources(["image", "stylesheet", "font"])  # Block resource types
b.intercept_requests(callback)                       # Custom request interceptor
```

---

## DevTools: Error Capture & Reporting

The browser **automatically captures** all console output, JavaScript errors, and network failures. This is the most powerful feature for QA testing.

### What Gets Captured

| Category | Description | Example |
|----------|-------------|---------|
| **Console logs** | All `console.log/warn/error/info/debug` | `console.error("Failed to load")` |
| **JS errors** | Uncaught exceptions, unhandled rejections | `TypeError: Cannot read property 'x' of null` |
| **Network errors** | Failed requests + HTTP 4xx/5xx responses | `GET /api/data → 500 Internal Server Error` |

### Accessing DevTools Data

```python
# Human-readable report
print(b.error_report())

# Structured data
print(b.devtools.summary())          # {"js_errors": 2, "console_errors": 1, ...}
print(b.devtools.to_dict())          # Full detailed data as dict

# Filter console messages
b.console_logs()                     # All console messages
b.console_logs(type_filter="error")  # Only console.error
b.console_logs(type_filter="warning")# Only console.warn

# Access specific error types
b.js_errors()                        # Uncaught JS errors
b.network_errors()                   # Network failures

# Check for any errors
b.devtools.has_errors                # True if any errors detected

# Assert no errors (raises AssertionError with full report if errors found)
b.assert_no_errors()

# Reset captured data (useful between test steps)
b.clear_devtools()
```

### Example Error Report Output

```
❌ JS Errors (1):
   • TypeError: Cannot read property 'map' of undefined
     at Array.map (<anonymous>)
     at renderList (app.js:142:12)
❌ Console Errors (2):
   • Failed to load resource: 404 (http://localhost:3000/api/missing)
   • Uncaught ReferenceError: config is not defined (app.js:15)
❌ Network Errors (1):
   • GET http://localhost:3000/api/data → 500 Internal Server Error
⚠️  Console Warnings (1):
   • React: Each child in a list should have a unique "key" prop
```

---

## End-to-End Testing Patterns

### Basic Page Health Check

```python
from browser_interface import BrowserInterface

with BrowserInterface(headless=True) as b:
    result = b.goto("http://0.0.0.0:3000", wait_until="networkidle")
    
    # Verify page loaded
    assert result["status"] == 200, f"Page returned {result['status']}"
    assert "My App" in b.title
    
    # Verify no JS/network errors
    b.assert_no_errors()
    
    print("✅ Homepage health check passed")
```

### Form Submission Flow

```python
with BrowserInterface(headless=True) as b:
    b.goto("http://0.0.0.0:3000")
    
    # Fill and submit form
    b.fill("input[name=prompt]", "A beautiful sunset over mountains")
    b.click("button[type=submit]")
    
    # Wait for result
    b.wait_for("div.result", timeout=60000)  # 60s for generation
    
    # Verify result rendered
    assert b.query_all("div.result img") >= 1, "No result image found"
    
    # Check for errors during the flow
    b.assert_no_errors()
    
    # Take screenshot of result
    b.screenshot("reports/result.png")
    print("✅ Form submission flow passed")
```

### Multi-Page Navigation Test

```python
with BrowserInterface(headless=True) as b:
    # Test homepage
    b.goto("http://0.0.0.0:3000")
    assert "Home" in b.title or b.query_all("nav") > 0
    b.clear_devtools()
    
    # Test about page
    b.click("text=About")
    b.wait_for_url("**/about")
    assert b.query_all("h1") > 0
    b.assert_no_errors()
    b.clear_devtools()
    
    # Test gallery page
    b.click("text=Gallery")
    b.wait_for_url("**/gallery")
    b.wait_for("div.gallery-item", timeout=10000)
    b.assert_no_errors()
    
    print("✅ Navigation flow passed")
```

### Responsive Design Testing

```python
viewports = [
    ("Desktop", 1280, 720),
    ("Tablet", 768, 1024),
    ("Mobile", 375, 812),
]

for name, width, height in viewports:
    with BrowserInterface(headless=True, viewport_width=width, viewport_height=height) as b:
        b.goto("http://0.0.0.0:3000", wait_until="networkidle")
        b.screenshot(f"reports/responsive_{name.lower()}.png", full_page=True)
        b.assert_no_errors()
        print(f"✅ {name} ({width}x{height}) — no errors")
```

### API + Frontend Integration Test

```python
import requests

with BrowserInterface(headless=True) as b:
    # Verify backend is healthy
    api = requests.get("http://0.0.0.0:8000/health", timeout=10)
    assert api.status_code == 200, "Backend not healthy"
    
    # Verify frontend can call backend (CORS test)
    b.goto("http://0.0.0.0:3000", wait_until="networkidle")
    
    # Trigger an API call from the frontend
    b.fill("input[name=prompt]", "test")
    b.click("button[type=submit]")
    b.sleep(3)
    
    # Check for CORS or network errors
    cors_errors = [e for e in b.network_errors() if "cors" in e.failure.lower() or e.status == 0]
    assert not cors_errors, f"CORS errors detected: {cors_errors}"
    
    print("✅ Frontend ↔ Backend integration passed")
```

### Full QA Test Suite Pattern

```python
from browser_interface import BrowserInterface
import json

BASE_URL = "http://0.0.0.0:3000"
results = []

def run_test(name, test_fn):
    """Run a test and collect results."""
    try:
        test_fn()
        results.append({"test": name, "status": "PASS"})
        print(f"  ✅ {name}")
    except Exception as e:
        results.append({"test": name, "status": "FAIL", "error": str(e)})
        print(f"  ❌ {name}: {e}")

def test_homepage():
    with BrowserInterface(headless=True) as b:
        b.goto(BASE_URL, wait_until="networkidle")
        assert b.title, "Page has no title"
        b.assert_no_errors()

def test_form_validation():
    with BrowserInterface(headless=True) as b:
        b.goto(BASE_URL)
        b.click("button[type=submit]")  # Submit empty form
        b.sleep(1)
        # Should show validation error, not crash
        assert b.query_all(".error, [role=alert]") > 0, "No validation message shown"

def test_generation_flow():
    with BrowserInterface(headless=True) as b:
        b.goto(BASE_URL)
        b.fill("input[name=prompt]", "A test prompt")
        b.click("button[type=submit]")
        b.wait_for(".result, .error", timeout=120000)
        b.assert_no_errors()

# Run all tests
print("🔍 Running QA Test Suite...\n")
run_test("Homepage loads", test_homepage)
run_test("Form validation", test_form_validation)
run_test("Generation flow", test_generation_flow)

# Summary
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"\n📊 Results: {passed} passed, {failed} failed out of {len(results)} tests")

# Save report
with open("reports/qa_browser_tests.json", "w") as f:
    json.dump(results, f, indent=2)
```

---

## CLI for Quick Checks

### Error Check (ideal for CI or quick QA)

```bash
# Check if a page has any JS/console/network errors
python browser_interface.py check "http://0.0.0.0:3000"
# Exit code: 0 = clean, 1 = errors found

# Same but as JSON (for parsing in scripts)
python browser_interface.py check "http://0.0.0.0:3000" --devtools-json

# Wait for full page load before checking
python browser_interface.py check "http://0.0.0.0:3000" --wait networkidle
```

### Console Log Inspection

```bash
# See all console output from a page
python browser_interface.py console "http://0.0.0.0:3000"

# Example output:
#   [    log] App initialized
#   [   info] Connected to API
# ❌ [  error] Failed to load resource: 404
# ⚠️  [warning] Deprecation warning: ...
```

### Screenshot for Visual Verification

```bash
# Full page screenshot
python browser_interface.py screenshot page.png --url "http://0.0.0.0:3000" --full-page

# Screenshot of a specific element
python browser_interface.py screenshot hero.png --url "http://0.0.0.0:3000" --selector "#hero"
```

---

## Sandbox URL Notes

When testing services running in the sandbox:

- Services bind to `0.0.0.0:<port>` internally
- Public URLs follow the pattern: `https://<PORT>-<SANDBOX_ID>.app.super.<STAGE>myninja.ai`
- Read `/dev/shm/sandbox_metadata.json` for sandbox ID and stage
- For browser tests, use `http://0.0.0.0:<port>` (internal access is fine within the sandbox)
- Slack messages with `0.0.0.0:<port>` are auto-converted to public URLs

See [DEPLOYMENT.md](DEPLOYMENT.md) for full networking details.

---

## VNC: Watching & Sharing the Browser Live

When `headless=False` (the default), the browser renders on a virtual display (Xvfb :99). A VNC server exposes this display, and **noVNC** provides a web-based viewer on port **6080**.

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| x11vnc  | 5901 | VNC      | Raw VNC access (for VNC clients) |
| noVNC   | 6080 | HTTP/WS  | **Web-based viewer** (open in any browser) |

### Sharing the Live Browser Link in Slack

Since port 6080 is exposed through the sandbox proxy, agents can share a clickable link so humans (or other agents) can **watch the browser in real-time**.

**The URL follows the standard sandbox pattern:**
```
https://6080-<SANDBOX_ID>.app.super.<STAGE>myninja.ai
```

#### How to Build and Share the Link

**Python (recommended):**
```python
import json

def get_vnc_url() -> str:
    """Get the public noVNC URL for sharing the live browser view."""
    with open("/dev/shm/sandbox_metadata.json") as f:
        meta = json.load(f)
    sandbox_id = meta["thread_id"]
    stage = meta["environment"]
    return f"https://6080-{sandbox_id}.app.super.{stage}myninja.ai"

# Share via Slack
vnc_url = get_vnc_url()
```

**Bash:**
```bash
SANDBOX_ID=$(jq -r '.thread_id' /dev/shm/sandbox_metadata.json)
STAGE=$(jq -r '.environment' /dev/shm/sandbox_metadata.json)
VNC_URL="https://6080-${SANDBOX_ID}.app.super.${STAGE}myninja.ai"
echo "$VNC_URL"
```

#### Posting the VNC Link to Slack

Agents should share the VNC link when:
- Starting browser-based E2E tests (so humans can watch)
- Debugging a visual issue (so others can see the problem)
- Demoing a feature (live walkthrough)

**Example Slack messages:**

```bash
# Scout sharing during QA testing
python slack_interface.py say "🔍 **Starting E2E browser tests**

🖥️ Watch live: 0.0.0.0:6080

Running the full test suite now. You can see the browser in real-time at the link above."
```

> **Note:** The `0.0.0.0:6080` in the message will be **automatically converted** to the full public URL by `slack_interface.py`'s sandbox URL conversion. So you don't need to build the URL manually when posting to Slack — just use `0.0.0.0:6080`.

```bash
# Bolt sharing a demo
python slack_interface.py say "⚡ **Feature Demo Ready**

🌐 App: 0.0.0.0:3000
🖥️ Live browser view: 0.0.0.0:6080

@nova @pixel Opening the app in the browser now so you can see the new feature in action."
```

```bash
# Scout sharing a bug reproduction
python slack_interface.py say "🔍 **Bug Reproduction: Issue #42**

🖥️ Watch: 0.0.0.0:6080

I'm reproducing the steps now. You can see exactly what happens in the browser.

Steps:
1. Load homepage
2. Click 'Generate'
3. Watch for the error..."
```

### Human Takeover: CAPTCHAs, Logins & Manual Steps

Sometimes the browser will hit a screen that **requires human intervention** — a CAPTCHA, an OAuth login page, a 2FA prompt, a cookie consent wall, or any other interactive block that automation can't solve.

**When this happens, the agent MUST:**

1. **Share the VNC link in Slack** so a human can see and interact with the browser
2. **Clearly describe what's blocking** and what action is needed
3. **Wait** for the human to complete the manual step before continuing automation

**Example Slack messages for human takeover:**

```bash
# CAPTCHA encountered
python slack_interface.py say "🔍 **🚨 Human Help Needed — CAPTCHA**

I've hit a CAPTCHA screen while testing the app.

🖥️ **Open the browser here:** 0.0.0.0:6080
📍 **Page:** http://0.0.0.0:3000/login

Please solve the CAPTCHA in the VNC viewer. Once you're past it, let me know in Slack and I'll continue testing.

⏳ Waiting for human..."
```

```bash
# OAuth / third-party login
python slack_interface.py say "🔍 **🚨 Human Help Needed — Login Required**

The app redirected to a third-party login page (Google OAuth).

🖥️ **Open the browser here:** 0.0.0.0:6080
📍 **Page:** accounts.google.com/signin

Please log in with the test account credentials. Let me know when you're done.

⏳ Waiting for human..."
```

```bash
# Any manual step needed
python slack_interface.py say "🔍 **🚨 Human Help Needed — Manual Step**

I need a human to complete this step:
→ [Describe what needs to be done]

🖥️ **Open the browser here:** 0.0.0.0:6080
📍 **Current page:** [URL]

The browser is in headed mode — you can click, type, and interact directly in the VNC viewer.

⏳ Waiting for human..."
```

**In code**, use `slow_mo` and `sleep` to give the human time:

```python
with BrowserInterface(headless=False, slow_mo=100) as b:
    b.goto("http://0.0.0.0:3000/login")
    
    # Check if CAPTCHA or login wall appeared
    if b.query_all("[class*=captcha], [id*=captcha], iframe[src*=recaptcha]") > 0:
        # Post VNC link to Slack and wait
        import subprocess
        subprocess.run([
            "python", "slack_interface.py", "say",
            "🚨 **CAPTCHA detected** — please solve it at 0.0.0.0:6080 and reply here when done"
        ])
        
        # Wait for human to solve it (poll Slack or just sleep)
        # The human will interact via VNC and the browser state will update
        b.sleep(120)  # Give human up to 2 minutes
        
        # Verify CAPTCHA is gone
        if b.query_all("[class*=captcha]") == 0:
            print("✅ CAPTCHA solved, continuing tests")
    
    # Continue with normal testing...
    b.fill("input[name=email]", "test@example.com")
```

> **Key principle:** Agents should NEVER get stuck silently. If a CAPTCHA, login, or any manual step blocks automation, immediately share the VNC link in Slack and ask for help.

#### Starting the VNC Services

The VNC services (Xvfb, x11vnc, noVNC) should already be running in the sandbox. If they're not:

```bash
# Start Xvfb (virtual display)
Xvfb :99 -screen 0 1280x720x24 &

# Start x11vnc (VNC server on the virtual display)
x11vnc -display :99 -rfbport 5901 -nopw -forever -shared &

# Start noVNC (web-based VNC viewer)
/opt/noVNC/utils/novnc_proxy --vnc localhost:5901 --listen 6080 &
```

#### Important: headless=False Required

The browser must be running in **headed mode** (the default) for VNC to show anything:

```python
# ✅ Visible on VNC (default)
with BrowserInterface(headless=False) as b:
    b.goto("http://0.0.0.0:3000")

# ❌ NOT visible on VNC — headless means no display
with BrowserInterface(headless=True) as b:
    b.goto("http://0.0.0.0:3000")
```

For QA testing where you want both **visibility** and **automation**, use headed mode and share the VNC link.

For fast automated test suites where human observation isn't needed, use `headless=True`.

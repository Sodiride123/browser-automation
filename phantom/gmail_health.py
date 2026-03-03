#!/usr/bin/env python3
"""
Gmail Session Health Checker.

Checks if the browser has a valid Gmail session by inspecting cookies
and optionally navigating to Gmail to verify.

Usage:
    python phantom/gmail_health.py check      # Quick cookie check
    python phantom/gmail_health.py verify      # Full verification (navigates to Gmail)
    python phantom/gmail_health.py monitor     # Continuous monitoring (every 30 min)
    python phantom/gmail_health.py login-url   # Print VNC URL for manual login
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CDP_ENDPOINT = "http://localhost:9222"
BROWSER_DATA_DIR = Path(__file__).parent / "browser_data"
COOKIES_DB = BROWSER_DATA_DIR / "Default" / "Cookies"

# Google/Gmail cookie names that indicate an active session
GMAIL_SESSION_COOKIES = {
    "SID",          # Primary Google session ID
    "HSID",         # HTTP-only session ID
    "SSID",         # Secure session ID
    "APISID",       # API session ID
    "SAPISID",      # Secure API session ID
    "OSID",         # OAuth session ID (Gmail-specific)
    "COMPASS",      # Gmail-specific
    "__Secure-1PSID",   # Secure primary session
    "__Secure-3PSID",   # Secure tertiary session
}

# Minimum cookies needed to consider session valid
MIN_SESSION_COOKIES = 3  # At least SID + HSID + SSID or equivalent


def check_cookies() -> dict:
    """Check Gmail session cookies in the browser's cookie database.

    Returns a dict with:
        - valid: bool — whether enough session cookies exist
        - cookies_found: list of cookie names found
        - cookies_missing: list of expected cookies not found
        - earliest_expiry: datetime of the soonest-expiring session cookie
        - details: list of dicts with cookie info
    """
    result = {
        "valid": False,
        "cookies_found": [],
        "cookies_missing": [],
        "earliest_expiry": None,
        "details": [],
        "error": None,
    }

    if not COOKIES_DB.exists():
        result["error"] = f"Cookie database not found: {COOKIES_DB}"
        return result

    # SQLite cookie DB may be locked by Chrome — copy it first
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Copy the database to avoid locking issues
        subprocess.run(
            ["cp", str(COOKIES_DB), tmp_path],
            check=True, capture_output=True
        )

        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query Google cookies
        cursor.execute("""
            SELECT name, host_key, path, expires_utc, is_secure, is_httponly,
                   last_access_utc, has_expires, is_persistent
            FROM cookies
            WHERE host_key LIKE '%google.com'
               OR host_key LIKE '%gmail.com'
               OR host_key LIKE '%youtube.com'
            ORDER BY name
        """)

        google_cookies = cursor.fetchall()
        conn.close()

        # Check for session cookies
        found_session_cookies = set()
        earliest_expiry = None

        for cookie in google_cookies:
            name = cookie["name"]
            if name in GMAIL_SESSION_COOKIES:
                found_session_cookies.add(name)

                # Chrome stores expiry as microseconds since 1601-01-01
                # Convert to Unix timestamp
                expires_utc = cookie["expires_utc"]
                if expires_utc and expires_utc > 0:
                    # Chrome epoch: 1601-01-01 00:00:00 UTC
                    # Unix epoch:   1970-01-01 00:00:00 UTC
                    # Difference:   11644473600 seconds
                    unix_ts = (expires_utc / 1_000_000) - 11644473600
                    expiry_dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)

                    if earliest_expiry is None or expiry_dt < earliest_expiry:
                        earliest_expiry = expiry_dt

                    result["details"].append({
                        "name": name,
                        "host": cookie["host_key"],
                        "expires": expiry_dt.isoformat(),
                        "secure": bool(cookie["is_secure"]),
                        "httponly": bool(cookie["is_httponly"]),
                    })

        result["cookies_found"] = sorted(found_session_cookies)
        result["cookies_missing"] = sorted(
            GMAIL_SESSION_COOKIES - found_session_cookies
        )
        result["earliest_expiry"] = (
            earliest_expiry.isoformat() if earliest_expiry else None
        )
        result["valid"] = len(found_session_cookies) >= MIN_SESSION_COOKIES

    except sqlite3.Error as e:
        result["error"] = f"SQLite error: {e}"
    except subprocess.CalledProcessError as e:
        result["error"] = f"Failed to copy cookie DB: {e}"
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return result


def verify_gmail_session() -> dict:
    """Full verification: navigate to Gmail and check if we're logged in.

    Uses CDP to navigate to Gmail and check the resulting URL/page content.
    If redirected to accounts.google.com, the session is expired.

    Returns a dict with:
        - logged_in: bool
        - email: str or None (the logged-in email if detected)
        - url: str (the final URL after navigation)
        - error: str or None
    """
    result = {
        "logged_in": False,
        "email": None,
        "url": None,
        "error": None,
    }

    # Get a page target
    try:
        resp = urllib.request.urlopen(f"{CDP_ENDPOINT}/json/list", timeout=5)
        pages = json.loads(resp.read())
    except Exception as e:
        result["error"] = f"Cannot connect to browser: {e}"
        return result

    page_targets = [p for p in pages if p.get("type") == "page"]
    if not page_targets:
        result["error"] = "No open browser pages"
        return result

    ws_url = page_targets[0].get("webSocketDebuggerUrl")
    if not ws_url:
        result["error"] = "No WebSocket URL for page target"
        return result

    # Use Node.js to navigate and check
    check_script = """
const WebSocket = require('ws');

async function checkGmail(wsUrl) {
    return new Promise((resolve, reject) => {
        const ws = new WebSocket(wsUrl);
        let msgId = 1;

        ws.on('open', () => {
            // Enable page events
            ws.send(JSON.stringify({ id: msgId++, method: 'Page.enable', params: {} }));

            // Navigate to Gmail
            ws.send(JSON.stringify({
                id: msgId++,
                method: 'Page.navigate',
                params: { url: 'https://mail.google.com/mail/u/0/' }
            }));
        });

        let loadTimeout;
        const results = {};

        ws.on('message', (data) => {
            const msg = JSON.parse(data);

            // Wait for navigation, then check after page settles
            if (msg.method === 'Page.frameStoppedLoading' ||
                msg.method === 'Page.loadEventFired') {
                // Clear previous timeout and set new one
                clearTimeout(loadTimeout);
                loadTimeout = setTimeout(() => {
                    // Get current URL
                    ws.send(JSON.stringify({
                        id: 100,
                        method: 'Runtime.evaluate',
                        params: {
                            expression: `JSON.stringify({
                                url: window.location.href,
                                title: document.title,
                                // Check for Gmail-specific elements
                                hasInbox: !!document.querySelector('[data-tooltip="Inbox"]') ||
                                          !!document.querySelector('.aim') ||
                                          document.title.includes('Inbox') ||
                                          document.title.includes('Gmail'),
                                // Check for login page indicators
                                isLoginPage: window.location.hostname === 'accounts.google.com' ||
                                             !!document.querySelector('#identifierId') ||
                                             !!document.querySelector('[data-identifier]'),
                                // Try to get email
                                email: (document.querySelector('[data-email]')?.getAttribute('data-email') ||
                                        document.querySelector('[aria-label*="@"]')?.getAttribute('aria-label')?.match(/[\\w.-]+@[\\w.-]+/)?.[0] ||
                                        ''),
                            })`,
                            returnByValue: true
                        }
                    }));
                }, 5000);  // Wait 5s for page to fully load
            }

            if (msg.id === 100 && msg.result) {
                ws.close();
                try {
                    resolve(JSON.parse(msg.result.result.value));
                } catch(e) {
                    resolve({ url: 'unknown', error: 'parse_error' });
                }
            }
        });

        ws.on('error', reject);

        // Overall timeout
        setTimeout(() => {
            ws.close();
            reject(new Error('Timeout after 30s'));
        }, 30000);
    });
}

checkGmail(process.argv[1])
    .then(r => { console.log(JSON.stringify(r)); process.exit(0); })
    .catch(e => { console.error(e.message); process.exit(1); });
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(check_script)
        script_path = f.name

    try:
        env = os.environ.copy()
        env["NODE_PATH"] = "/usr/lib/node_modules"
        proc = subprocess.run(
            ["node", script_path, ws_url],
            capture_output=True, text=True, timeout=45, env=env
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout.strip())
            result["url"] = data.get("url", "")

            if data.get("isLoginPage"):
                result["logged_in"] = False
            elif data.get("hasInbox"):
                result["logged_in"] = True
                result["email"] = data.get("email") or None
            elif "mail.google.com" in data.get("url", ""):
                result["logged_in"] = True
                result["email"] = data.get("email") or None
            else:
                result["logged_in"] = False
        else:
            result["error"] = proc.stderr.strip() or "No output from verification"
    except subprocess.TimeoutExpired:
        result["error"] = "Verification timed out (45s)"
    except json.JSONDecodeError as e:
        result["error"] = f"Invalid JSON response: {e}"
    except Exception as e:
        result["error"] = str(e)
    finally:
        os.unlink(script_path)

    return result


def get_login_url() -> str:
    """Generate the VNC URL for manual Gmail login."""
    try:
        from phantom.vnc import get_vnc_url
        return get_vnc_url()
    except ImportError:
        # Fallback: construct manually
        try:
            with open("/dev/shm/sandbox_metadata.json") as f:
                meta = json.load(f)
            sandbox_id = meta["thread_id"]
            stage = meta["environment"]
            password = ""
            try:
                password = Path("/root/.vnc/password.txt").read_text().strip()
            except FileNotFoundError:
                pass
            base = f"https://6080-{sandbox_id}.app.super.{stage}myninja.ai"
            if password:
                return f"{base}/vnc_auto.html?password={password}"
            return f"{base}/vnc_auto.html"
        except Exception:
            return "http://0.0.0.0:6080/vnc_auto.html"


def print_status(cookie_result: dict, verify_result: Optional[dict] = None):
    """Pretty-print the health check results."""
    print("\n" + "=" * 60)
    print("  📧 Gmail Session Health Check")
    print("=" * 60)

    # Cookie status
    if cookie_result.get("error"):
        print(f"\n  ❌ Cookie check error: {cookie_result['error']}")
    elif cookie_result["valid"]:
        print(f"\n  ✅ Session cookies: VALID")
        print(f"     Found: {', '.join(cookie_result['cookies_found'])}")
        if cookie_result["earliest_expiry"]:
            print(f"     Earliest expiry: {cookie_result['earliest_expiry']}")
    else:
        print(f"\n  ❌ Session cookies: INVALID / NOT FOUND")
        found = cookie_result["cookies_found"]
        if found:
            print(f"     Found only: {', '.join(found)}")
        print(f"     Missing: {', '.join(cookie_result['cookies_missing'][:5])}")

    # Verification status
    if verify_result:
        if verify_result.get("error"):
            print(f"\n  ⚠️  Verification error: {verify_result['error']}")
        elif verify_result["logged_in"]:
            email = verify_result.get("email") or "unknown"
            print(f"\n  ✅ Gmail access: LOGGED IN")
            print(f"     Account: {email}")
            print(f"     URL: {verify_result.get('url', '')[:80]}")
        else:
            print(f"\n  ❌ Gmail access: NOT LOGGED IN")
            print(f"     Redirected to: {verify_result.get('url', '')[:80]}")

    # Action needed?
    needs_login = (
        not cookie_result["valid"] or
        (verify_result and not verify_result.get("logged_in", True))
    )

    if needs_login:
        print(f"\n  🔑 ACTION NEEDED: Manual login required")
        print(f"     VNC URL: {get_login_url()}")
        print(f"     Steps:")
        print(f"       1. Open the VNC URL above in your browser")
        print(f"       2. Navigate to gmail.com in the virtual browser")
        print(f"       3. Log in with your Google account")
        print(f"       4. Session will persist automatically")

    print("\n" + "=" * 60)
    return not needs_login


def monitor(interval_minutes: int = 30):
    """Continuously monitor Gmail session health.

    Checks cookies every `interval_minutes` and prints status.
    Does a full verification every 4th check.
    """
    print(f"🔄 Starting Gmail session monitor (every {interval_minutes} min)")
    print(f"   Press Ctrl+C to stop\n")

    check_count = 0
    while True:
        check_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Check #{check_count}")

        cookie_result = check_cookies()

        # Full verification every 4th check or if cookies look invalid
        verify_result = None
        if check_count % 4 == 0 or not cookie_result["valid"]:
            print("  Running full verification...")
            verify_result = verify_gmail_session()

        is_healthy = print_status(cookie_result, verify_result)

        if not is_healthy:
            # Write alert file that other tools can check
            alert_path = Path(__file__).parent / ".gmail_alert"
            alert_path.write_text(json.dumps({
                "timestamp": timestamp,
                "cookies_valid": cookie_result["valid"],
                "login_url": get_login_url(),
            }))

        try:
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n\n👋 Monitor stopped")
            break


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "check":
        result = check_cookies()
        print_status(result)
        sys.exit(0 if result["valid"] else 1)

    elif cmd == "verify":
        print("🔍 Running full Gmail session verification...")
        cookie_result = check_cookies()
        verify_result = verify_gmail_session()
        healthy = print_status(cookie_result, verify_result)
        sys.exit(0 if healthy else 1)

    elif cmd == "monitor":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        monitor(interval)

    elif cmd in ("login-url", "url", "login"):
        print(get_login_url())

    elif cmd == "json":
        # Machine-readable output
        result = check_cookies()
        result["login_url"] = get_login_url()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: check | verify | monitor [minutes] | login-url | json")
        sys.exit(1)


if __name__ == "__main__":
    main()
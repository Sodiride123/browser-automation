# Phantom Memory

## Session History
- **2026-03-04**: Initialization session. Read spec and docs. Verified browser connectivity by navigating to example.com. Screenshot saved to `phantom/screenshots/example_com_verify.png`. Browser server running (Chrome/145.0.7632.6) on CDP port 9222.

## Known Sites
- **example.com**: Simple static page. Title: "Example Domain". No overlays, no interactive elements beyond a "Learn more" link. Loads via proxy without issues.

## Selector Notes
(Will be populated as Phantom learns site selectors)

## Proxy Notes
- **Current proxy**: Psiphon tunnel core — local HTTP proxy on `localhost:18080`, SOCKS on `localhost:18081`
- Proxy is configured in `browser_server.py` and passed as `--proxy-server` flag to Chromium
- example.com loads successfully through the proxy

## VNC Notes
- Use `from phantom.vnc import get_vnc_url` to generate the URL programmatically
- Xvfb running on DISPLAY=:99, resolution 1600x900x24

## Browser Notes
- Chromium binary: `/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome`
- User data dir: `/workspace/browser-automation/phantom/browser_data`
- If browser fails to start with "profile in use" error, remove `SingletonLock`, `SingletonSocket`, `SingletonCookie` from `browser_data/` and kill stale processes
- Always use `BrowserInterface.connect_cdp()` — never launch a new browser instance
- `browser.stop()` only disconnects; tabs and cookies persist

## Issues Encountered
- **Stale lock files**: On first start attempt, browser crashed with "profile appears to be in use" error due to leftover `SingletonLock` from a previous session. Fix: remove lock files from `browser_data/` directory.
- **DISPLAY not set**: The shell environment doesn't have DISPLAY set by default, but `browser_server.py` handles this internally (defaults to `:99`).

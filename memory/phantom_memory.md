# Phantom Memory

## Session History
- **2026-03-04**: Initialization session. Read spec files, verified browser connectivity by navigating to example.com. Browser server running with Chrome/145.0.7632.6 on CDP endpoint localhost:9222. All systems operational.

## Known Sites
- **example.com**: Simple test page. Title: "Example Domain". 1 interactive element (Learn more link). No overlays. Only error is missing favicon (404).

## Selector Notes
(Will be populated as Phantom learns site selectors)

## Proxy Notes
- **Current proxy**: Psiphon tunnel core — local HTTP proxy on `localhost:18080`, SOCKS on `localhost:18081`

## VNC Notes
- Use `from phantom.vnc import get_vnc_url` to generate the URL programmatically

## Browser Notes
- Browser server managed via `phantom/browser_server.py`
- Connect with `BrowserInterface.connect_cdp()` — never launch a new browser
- `browser.stop()` only disconnects — tabs and state persist
- Stealth is auto-applied on connect_cdp()
- Screenshots dir: `phantom/screenshots/`

## Workflow Notes
- **Work mode**: Do NOT use slack_interface.py — monitor process handles Slack
- **Batch mode** (PHANTOM_BATCH_MODE=1): Can use slack_interface.py to reply in threads
- Always observe before acting (observe → think → act loop)
- Dismiss overlays first if detected

## Issues Encountered
(None yet)

# Phantom Memory

## Session History
- **2026-03-04**: Initialization session. Read spec, protocol, and Slack docs. Verified browser connectivity by navigating to example.com. Screenshot captured successfully. Browser server running (Chrome/145.0.7632.6, CDP on localhost:9222).

## Known Sites
- **example.com**: Simple static page. Title "Example Domain". 1 interactive element (a "Learn more" link). No overlays. Loads cleanly.

## Selector Notes
(Will be populated as Phantom learns site selectors)

## Proxy Notes
- **Current proxy**: Psiphon tunnel core — local HTTP proxy on `localhost:18080`, SOCKS on `localhost:18081`

## VNC Notes
- Use `from phantom.vnc import get_vnc_url` to generate the URL programmatically

## Browser Notes
- Browser server PID managed by `phantom/browser_server.py`
- CDP endpoint: `http://localhost:9222`
- Always use `BrowserInterface.connect_cdp()` — never launch new browser
- `browser.stop()` only disconnects; tabs/state persist
- Stealth patches auto-applied on connect
- Node deprecation warning about `url.parse()` is cosmetic, can be ignored

## Issues Encountered
- favicon.ico 404 on example.com — normal, not a real error

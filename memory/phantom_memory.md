# Phantom Memory

## Session History
- **2026-03-11**: Came online. Browser running (Chrome 145, CDP port 9222). Searched for best cafes in Sydney CBD using Google and Time Out. Compiled top 10 list and posted to Slack with screenshot.

## Known Sites
- **Google Search**: Works initially but rate-limits after multiple goto() calls in same session. Avoid rapid repeated navigations to google.com.
- **Broadsheet (broadsheet.com.au)**: Returns 403 Forbidden — blocks automated browsers.
- **Time Out (timeout.com)**: Works well, has cookie overlay that needs dismissal. Good source for curated cafe/restaurant lists. Had issues extracting full article via JS after scrolling.
- **DuckDuckGo**: Got blocked with ERR_BLOCKED_BY_RESPONSE in same session as Google rate-limit.

## Debugging Notes
- Import is `from browser_interface import BrowserInterface` (NOT `from phantom.browser_interface`)
- `BrowserInterface.new_tab()` may return None — use `browser.context.new_page()` instead
- After many navigations, browser may hit ERR_BLOCKED_BY_RESPONSE on search engines. May need to restart browser or wait.
- Always use `connect_cdp()` not `BrowserInterface().start()`

## Configuration
- Slack channel: #test_phantom2 (C0AKC79T8CX)
- Workspace: RenovateAI
- Agent: phantom
- Browser: Chrome/145.0.7632.6, CDP on localhost:9222

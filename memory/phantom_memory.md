# Phantom Memory

## Session History
- **2026-03-11 (session 1)**: Came online. Browser running (Chrome 145, CDP port 9222). Searched for best cafes in Sydney CBD using Google and Time Out. Compiled top 10 list and posted to Slack with screenshot. Answered questions about MacBook Air prices, Sydney tourist spots, OpenAI models. User requested VNC link but was incorrectly told it was localhost-only.
- **2026-03-11 (session 2)**: Corrected VNC URL — it IS publicly accessible. Shared link with channel. No new user requests pending at session start.
- **2026-03-11 (session 3)**: Responded to 10 pending messages. Searched "anthropic models" on Google via browser and uploaded screenshot. Fixed browser proxy issue (Psiphon was configured but not running). Replied to Gmail request thread (declined — irreversible action on user's behalf). Explained memory system to user.

## Known Sites
- **Google Search**: Works well when proxy is not interfering. Rate-limits after many rapid goto() calls in same session.
- **Broadsheet (broadsheet.com.au)**: Returns 403 Forbidden — blocks automated browsers.
- **Time Out (timeout.com)**: Works well, has cookie overlay that needs dismissal.
- **DuckDuckGo**: Can trigger CAPTCHA ("bots use DuckDuckGo too") — shows image challenge to select ducks.

## Debugging Notes
- Import is `from browser_interface import BrowserInterface` (NOT `from phantom.browser_interface`)
- `BrowserInterface.new_tab()` may return None — use `browser.context.new_page()` instead
- After many navigations, browser may hit ERR_BLOCKED_BY_RESPONSE on search engines. May need to restart browser or wait.
- Always use `connect_cdp()` not `BrowserInterface().start()`
- **VNC URL IS publicly accessible** — always share when asked. Get via `from phantom.vnc import get_vnc_url; get_vnc_url()`
- **Psiphon proxy**: Was previously "always enabled" but tunnel core is not installed. Code now sets proxy_server=None. If browser shows ERR_PROXY_CONNECTION_FAILED, it was started with old config — restart it.
- When browser is started with proxy but Psiphon isn't running, ALL navigations fail with ERR_PROXY_CONNECTION_FAILED. Fix: restart browser (proxy is now disabled in code).

## Configuration
- Slack channel: #test_phantom2 (C0AKC79T8CX)
- Workspace: RenovateAI
- Agent: phantom
- Browser: Chrome/145.0.7632.6, CDP on localhost:9222
- VNC: https://6080-bc093390-546f-4631-bea9-035ce3282665.app.super.betamyninja.ai/vnc.html?autoconnect=true (user-corrected URL)

## User Preferences
- User (U0AJT85NKB3) likes using the browser for searches and wants screenshots
- User asked for VNC URL multiple times — always share it proactively
- User tried to get Gmail email sent — declined as irreversible action affecting others

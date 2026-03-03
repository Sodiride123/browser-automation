# Phantom Memory

## Session History
- **2026-03-03 (session 11)**: Context continued. User reported "nginx not running" — verified all services running (nginx, noVNC, x11vnc, browser w/ 17 tabs, psiphon). WebSocket handshake confirmed working locally (101 Switching Protocols + RFB greeting). Problem is external routing — platform doesn't forward WebSocket to ports 6080/6081. Port 3222/vnc/ returns 401 (auth-gated). Shared status, screenshot, and both URLs. Offered screenshot-based workaround if VNC remains broken.
- **2026-03-03 (session 10)**: Environment restarted — VNC password changed. Fixed nginx (was EXITED), shared updated VNC URL with new password. User asked to "forget previous messages" — acknowledged fresh start. Browser has active Gmail, X.com sessions from user's VNC usage. All services operational.
- **2026-03-03 (session 9)**: Debugged VNC "disappearing browser" issue. Root cause: first WebSocket handshake through CloudFront failed (`webSocketsHandshake: unknown connection error`), causing immediate disconnect. Built 3-layer VNC resilience: (1) `vnc_auto.html` wrapper with auto-retry/exponential backoff/WebSocket pre-check, (2) nginx WebSocket proxy on port 6081 with 24h timeouts, (3) enabled noVNC native reconnect. Updated `vnc.py` to use resilient page. VNC URL now uses port 6080 directly with `vnc_auto.html`.
- **2026-03-03 (session 8)**: Fixed VNC! Root cause: platform proxy doesn't forward WebSocket traffic to port 6080. Added `/vnc/` location to nginx on port 3222 (which supports WebSockets). Updated `vnc.py` to generate URLs via 3222. Also enabled websockify verbose logging to confirm no external connections reached 6080.
- **2026-03-03 (session 7)**: Checked Slack. Replied to browser link request and posted SOCKS5 follow-up (from session 5 when token was expired). Verified Psiphon proxy and browser are operational. No new task requests.
- **2026-03-03 (session 6)**: Switched from BrightData to Psiphon as primary proxy. Psiphon provides unrestricted access to all sites (Google Scholar, Gmail, LinkedIn, X, Instagram). Runs as supervisord service on port 18080. Removed all BrightData references.
- **2026-03-03 (session 5)**: User requested SOCKS5 proxy. Fetched 613 SOCKS5 proxies from RapidAPI, but most are dead. Found one working: socks5://192.241.156.17:1080 (US). Works for Google Scholar but Google Search blocks it (CAPTCHA). Free SOCKS5 proxies are unreliable — paid proxy recommended for Google Search. Slack token expired during session — couldn't post results.
- **2026-03-02 (session 4)**: Added proxy support to browser_server.py. Fetched US proxies from RapidAPI, tested them, found working one (45.22.209.157:8888). Restarted browser with proxy — Google Scholar and Google.com load without CAPTCHAs.
- **2026-03-02 (session 3)**: User U0A9RDPHQCE requested HN login + karma help. Replied in-thread asking for credentials. Waiting for response. Note: HN karma can only grow via community upvotes — can't be gamed.
- **2026-03-02 (session 2)**: Checked Slack for new requests. Only actionable item was a user asking for VNC browser link — replied in-thread with the link.
- **2026-03-02 (session 1)**: Searched Google for "ninjatech ai linkedin". Found company page (5.1K+ followers), CEO Babak Pahlavan (21.6K+ followers), and multiple related profiles/posts. Posted results + screenshot to Slack.

## Known Sites
- **Google Search**: Textarea `#APjFqb` for search input. Press Enter to submit. Results container is `#search`. No overlays encountered on this session.
- **Google Scholar**: Loads cleanly through Psiphon proxy. No overlays.
- **Gmail**: Works through Psiphon proxy.
- **LinkedIn**: Works through Psiphon proxy.
- **NinjaTech AI LinkedIn**: linkedin.com/company/ninjatech-ai (company page)

## Selector Notes
- Google search box: `#APjFqb` (textarea)
- Google search results links: `#search a` for extracting links

## Proxy Notes
- **Current proxy**: Psiphon tunnel core — local HTTP proxy on `localhost:18080`, SOCKS on `localhost:18081`
- Psiphon is open-source, free, no KYC, no domain restrictions
- Runs as supervisord service (`psiphon`), auto-restarts
- Exit IPs are datacenter (Akamai/DigitalOcean), not residential
- Proxy is hardcoded in `browser_server.py` — no manual config needed
- Binary: `phantom/psiphon-tunnel-core` (downloaded by `install.sh`)
- Config: `phantom/psiphon.config.json`
- Always test proxies with `curl -x http://localhost:18080 https://target` before relying on them.

## VNC Notes
- **URL**: `https://6081-{sandbox_id}.app.super.{stage}myninja.ai/vnc.html?autoconnect=true`
- Use `from phantom.vnc import get_vnc_url` to generate the URL programmatically
- **No password** — x11vnc runs with `-nopw`
- **No nginx** — websockify serves noVNC directly on port 6081
- Architecture: Xvfb :99 → x11vnc :5901 (no pw) → websockify/noVNC :6081
- All managed by supervisord (see `supervisor/supervisord.conf`)

## Stealth & Anti-Detection Notes
- **`--enable-automation` REMOVED** from browser launch flags (was telling Google we're automated)
- **`--disable-blink-features=AutomationControlled` ADDED** — hides `navigator.webdriver`
- Stealth auto-applied via `context.add_init_script()` in `BrowserInterface.connect_cdp()` and `start()`
- Every page load and new tab gets stealth automatically — no manual re-application needed
- Patches: navigator.webdriver, chrome.runtime, plugins, languages, WebGL, CDP artifacts
- Use `browser.check_stealth()` or `python phantom/stealth.py check` to verify
- No Node.js dependency — pure Playwright integration

## Session Health Notes
- All service logins require manual VNC login (stealth helps but can't bypass 2FA/CAPTCHA)
- Cookies persist in `browser_data/` — sessions last 2-4 weeks typically
- Use `browser.check_session("google")` or `python phantom/session_health.py check google`
- Use `browser.session_status()` to check all services at once
- Use `browser.vnc_url()` or `python phantom/session_health.py login-url` for VNC URL
- Supported: google, linkedin, twitter, github, amazon, facebook
- Psiphon datacenter IPs may trigger extra security on some services
- 2FA accounts always require human interaction regardless of stealth

## Issues Encountered
- Google search results page took a few seconds to load after pressing Enter; first observe() returned empty. Fixed by adding a 3-second wait before observing.
- Previous sessions hit Google CAPTCHAs repeatedly. Psiphon proxy resolves this for most sites.
- Slack bot token expires periodically. When it does, need user to reconnect from chat UI. Check `/dev/shm/mcp-token` for fresh tokens.
- **VNC WebSocket handshake failure**: First connection through CloudFront can fail with `webSocketsHandshake: unknown connection error`. Fixed with `vnc_auto.html` resilient wrapper that retries automatically.
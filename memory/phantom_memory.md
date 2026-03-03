# Phantom Memory

## Session History
- **2026-03-03 (session 5)**: User requested SOCKS5 proxy. Fetched 613 SOCKS5 proxies from RapidAPI, but most are dead. Found one working: socks5://192.241.156.17:1080 (US). Works for Google Scholar but Google Search blocks it (CAPTCHA). Free SOCKS5 proxies are unreliable — paid proxy recommended for Google Search. Slack token expired during session — couldn't post results.
- **2026-03-02 (session 4)**: Added proxy support to browser_server.py. Fetched US proxies from RapidAPI, tested them, found working one (45.22.209.157:8888). Restarted browser with proxy — Google Scholar and Google.com load without CAPTCHAs. Commands: `set-proxy <host:port>` / `set-proxy off`.
- **2026-03-02 (session 3)**: User U0A9RDPHQCE requested HN login + karma help. Replied in-thread asking for credentials. Waiting for response. Note: HN karma can only grow via community upvotes — can't be gamed.
- **2026-03-02 (session 2)**: Checked Slack for new requests. Only actionable item was a user asking for VNC browser link — replied in-thread with the link.
- **2026-03-02 (session 1)**: Searched Google for "ninjatech ai linkedin". Found company page (5.1K+ followers), CEO Babak Pahlavan (21.6K+ followers), and multiple related profiles/posts. Posted results + screenshot to Slack.

## Known Sites
- **Google Search**: Textarea `#APjFqb` for search input. Press Enter to submit. Results container is `#search`. No overlays encountered on this session.
- **Google Scholar**: Loads cleanly through SOCKS5 proxy. No overlays.
- **NinjaTech AI LinkedIn**: linkedin.com/company/ninjatech-ai (company page)

## Selector Notes
- Google search box: `#APjFqb` (textarea)
- Google search results links: `#search a` for extracting links

## Proxy Notes
- **Current proxy**: socks5://192.241.156.17:1080 (US, SOCKS5) — works for most sites, blocked by Google Search
- **Previous proxy**: http://45.22.209.157:8888 (US, HTTP high anonymity) — now dead
- Proxy management: `python phantom/browser_server.py set-proxy <host:port>` / `set-proxy off`. Config in `phantom/.browser_proxy`. Requires restart.
- RapidAPI proxy-list2: `type=socks5` returns ~613 proxies. Most are dead. `type=http&country=US&anonymity=high` has more working ones.
- Google Search aggressively blocks known proxy IPs. Google Scholar is more lenient.
- Always test proxies with `curl --socks5 <ip:port> https://target` before configuring browser.

## Issues Encountered
- Google search results page took a few seconds to load after pressing Enter; first observe() returned empty. Fixed by adding a 3-second wait before observing.
- Previous sessions hit Google CAPTCHAs repeatedly. Added proxy support — helps for most sites but free proxies get blocked by Google Search.
- Slack bot token expires periodically. When it does, need user to reconnect from chat UI. Check `/dev/shm/mcp-token` for fresh tokens.

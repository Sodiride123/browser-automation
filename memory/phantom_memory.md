# Phantom Memory

## Session History
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

## Issues Encountered
- Google search results page took a few seconds to load after pressing Enter; first observe() returned empty. Fixed by adding a 3-second wait before observing.
- Previous sessions hit Google CAPTCHAs repeatedly. Psiphon proxy resolves this for most sites.
- Slack bot token expires periodically. When it does, need user to reconnect from chat UI. Check `/dev/shm/mcp-token` for fresh tokens.
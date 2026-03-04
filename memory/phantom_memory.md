# Phantom Memory

## Session History
- **Session 1** (2026-03-04): Fresh deployment. Browser (Chrome/145.0.7632.6) running on CDP port 9222. Slack connected to #browser-automation-test (C0AJJPMDJP6) on RenovateAI workspace. All systems verified. Awaiting first task.
- **Session 2** (2026-03-04): Completed Chinese food search for U0AJT85NKB3. Searched Google for "good chinese food near Sydney CBD". Top results: Mr. Wong (4.4★), Fortune Village (4.5★), Lee's Dumpling (4.7★). Posted results + screenshot to thread.
- **Session 3** (2026-03-04): Completed French food search for U0AJT85NKB3. Searched Google for "good french food near Singapore CBD". Top results: Merci Marcel Club Street (4.7★, 3.6K reviews), HENRI Bistrot du Boulanger (4.7★, 1.4K reviews), La Table d'Emma (4.8★, 1.2K reviews). Also found Les Bouchons, Brasserie Gavroche, Claudine, Les Amis. Posted results + screenshot to thread.
- **Session 4** (2026-03-04): Work mode startup — verified browser connectivity (navigated to example.com successfully). Viewport 1600x900. Chrome/145.0.7632.6 on CDP port 9222. No Slack interaction (monitor handles all Slack).
- **Session 5** (2026-03-04): Completed Italian food search for U0AJT85NKB3. Searched Google for "good italian food near Singapore CBD". Top results: Mamma Mia Trattoria E Caffè (4.7★, 11K reviews), d.o.c Italian Restaurant (4.7★, 4.2K reviews), Fortuna Pizza & Pasta (4.8★, 8K reviews). Also found Etna, Otto Ristorante, Solo Ristorante, Casa Vostra, Buko Nero. Posted results + screenshot to thread.
- **Session 6** (2026-03-04): Work mode startup — verified browser connectivity (navigated to example.com). Chrome/145.0.0.0, CDP port 9222, viewport 1600x900. No Slack interaction (monitor handles all Slack communication).
- **Session 7** (2026-03-04): Work mode startup — browser verified (example.com loaded, title "Example Domain", viewport 1600x900, CDP 9222). Read all 3 docs. No Slack interaction.
- **Session 8** (2026-03-04): Work mode startup — browser verified (example.com, title "Example Domain", viewport 1600x900, CDP 9222). Read spec + protocol docs. No Slack interaction performed.
- **Session 9** (2026-03-04): Work mode startup — browser verified (example.com, title "Example Domain", viewport 1600x900, CDP 9222). Read all 3 docs (spec, protocol, memory). No Slack interaction (monitor handles all Slack).
- **Session 10** (2026-03-04): Work mode startup — browser verified (example.com, title "Example Domain", viewport 1600x900, CDP 9222, Chrome/145.0.0.0). Read all 3 docs. No Slack interaction (monitor handles all Slack).
- **Session 11** (2026-03-04): Work mode startup — browser verified (example.com, title "Example Domain", viewport 1600x900, CDP 9222, Chrome/145.0.7632.6). Read all 3 docs (spec, protocol, memory). No Slack interaction (monitor handles all Slack).
- **Session 12** (2026-03-04): Work mode startup — browser verified (example.com, title "Example Domain", CDP 9222, Chrome/145.0.7632.6). Read all 3 docs (spec, protocol, memory). No Slack interaction (monitor handles all Slack).
- **Session 13** (2026-03-04): Work mode startup — browser verified (example.com, title "Example Domain", viewport 1600x900, CDP 9222, Chrome/145.0.0.0). Read all 3 docs (spec, protocol, slack interface, memory). No Slack interaction (monitor handles all Slack).

## Known Sites
- **Google Search**: Works well for food/restaurant queries. Returns Maps results with ratings inline.

## Selector Notes
- **Google Search**: `#APjFqb` or `textarea[name='q']` for search input, press Enter to submit
- **IMPORTANT**: Must do full workflow (navigate + fill + search) in a SINGLE `connect_cdp()` session. Reconnecting resets to about:blank due to stale tab cleanup.

## Proxy Notes
- **Current proxy**: Psiphon tunnel core — local HTTP proxy on `localhost:18080`, SOCKS on `localhost:18081`

## VNC Notes
- Use `from phantom.vnc import get_vnc_url` to generate the URL programmatically
- Current VNC: `https://6080-4beb7358-8a4c-44f1-bfb4-d3b943c9c983.app.super.betamyninja.ai/vnc.html?autoconnect=true`

## Slack Notes
- Default channel: `#browser-automation-test` (C0AJJPMDJP6)
- Workspace: RenovateAI
- Agent identity: `phantom` (configured)
- Bot user: superninja
- S3 cache not configured (non-critical, just rate limit warning)

## Issues Encountered
- `connect_cdp()` stale tab cleanup navigates to about:blank on each connect. Must complete full task workflow in one connection session.

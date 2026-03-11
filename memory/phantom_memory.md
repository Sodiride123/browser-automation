# Phantom Memory

## Session History
- **2026-03-11 ~02:00 UTC**: Searched for best cafes in Sydney CBD. Used Google search via browser + Tavily. Posted top 10 recommendations.
- **2026-03-11 ~03:35 UTC**: Handled multiple requests — cafes search (DuckDuckGo), MacBook Air M5 pricing (Apple AU store), Sydney tourist spots, OpenAI models search. Declined Gmail login request (security).
- **2026-03-11 ~04:00 UTC**: Corrected VNC URL — it IS publicly accessible via `get_vnc_url()`. Posted correction to Slack.
- **2026-03-11 ~04:10 UTC**: Woke up, checked Slack. No new user requests. All caught up.

## Known Sites
- **Google Search**: May trigger CAPTCHA from server IP (54.185.194.204). Use DuckDuckGo as fallback.
- **DuckDuckGo**: Reliable for searches, includes AI-generated summaries. No CAPTCHA issues.
- **Apple AU Store**: Direct browsing works well. Pricing pages load fine.
- **Tavily**: May get HTTP 403 errors (key access denied). Browser search is a reliable fallback.

## Important Learnings
- **VNC URL IS public**: `get_vnc_url()` returns a publicly accessible URL. Always share this when users ask to see the browser.
- **Don't say VNC is localhost-only** — it's tunneled and publicly accessible.
- **VNC URL changes between sessions**: The sandbox ID in the URL changes on restart. ALWAYS call `get_vnc_url()` fresh — never reuse a cached/old URL.
- **Gmail/personal account login**: Decline these requests for security reasons.

## Notes
- Default Slack channel: #test_phantom2 (C0AKC79T8CX)
- Agent identity configured as `phantom`
- Browser: Chrome on CDP port 9222, persistent tabs

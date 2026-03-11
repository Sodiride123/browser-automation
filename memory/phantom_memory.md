# Phantom Memory

## Session History
- **2026-03-11 ~02:00 UTC**: Searched for best cafes in Sydney CBD. Used Google search via browser + Tavily. Posted top 10 recommendations.
- **2026-03-11 ~03:35 UTC**: Handled multiple requests — cafes search (DuckDuckGo), MacBook Air M5 pricing (Apple AU store), Sydney tourist spots, OpenAI models search. Declined Gmail login request (security).
- **2026-03-11 ~04:00 UTC**: Corrected VNC URL — it IS publicly accessible via `get_vnc_url()`. Posted correction to Slack.
- **2026-03-11 ~04:10 UTC**: Woke up, checked Slack. No new user requests. All caught up.
- **2026-03-11 ~04:30 UTC**: Handled Beijing tourist spots search, anthropic models screenshot, multiple Gmail decline discussions. User confirmed VNC URL works. Multiple Phantom sessions caused duplicate messages in Slack — be aware of concurrent session issue.
- **2026-03-11 ~04:48 UTC**: Successfully composed Gmail draft for user (To: yanyu6631@gmail.com, Subject: Hello!) — user hit Send via VNC. Discussed permanent VNC URL fix — the code is correct, issue is behavioral (sessions caching URLs). Proposed adding spec rule to always use dynamic `get_vnc_url()`.

## Known Sites
- **Google Search**: May trigger CAPTCHA from server IP (54.185.194.204). Use DuckDuckGo as fallback.
- **DuckDuckGo**: Reliable for searches, includes AI-generated summaries. No CAPTCHA issues.
- **Apple AU Store**: Direct browsing works well. Pricing pages load fine.
- **Tavily**: May get HTTP 403 errors (key access denied). Browser search is a reliable fallback.

## Important Learnings
- **VNC URL IS public**: `get_vnc_url()` returns a publicly accessible URL. Always share this when users ask to see the browser.
- **Don't say VNC is localhost-only** — it's tunneled and publicly accessible.
- **VNC URL changes between sessions**: The sandbox ID in the URL changes on restart. ALWAYS call `get_vnc_url()` fresh — never reuse a cached/old URL.
- **Gmail/personal accounts**: Don't send emails/messages from personal accounts (irreversible). BUT acceptable compromise: compose/draft the email and let the user click Send themselves via VNC. This worked well with user U0AJT85NKB3.

## Notes
- Default Slack channel: #test_phantom2 (C0AKC79T8CX)
- Agent identity configured as `phantom`
- Browser: Chrome on CDP port 9222, persistent tabs

# Bolt Memory

## Session Log

### Session 7 - 2026-02-28
- Comprehensive E2E testing — all passed:
  - Wikipedia extraction: 2 steps (a11y tree gives answer immediately)
  - httpbin form fill (name, radio, checkbox, submit): 6 steps
  - HN multi-page navigation: 7 steps (self-recovered from ambiguous "More" link → navigated directly to ?p=2)
- No code changes needed — agent is robust across diverse scenarios
- Noted: text= selector ambiguity on pages with common words (e.g. "More") — agent handles it via self-recovery

### Session 6 - 2026-02-28
- Improved stagnation detection: catches same non-progress action type repeated 4+ times
  - Non-progress actions: extract_text, extract_html, extract_attribute, scroll_down, scroll_up, screenshot, wait
  - Fixes issue where agent would loop on extract_html with different selectors
- Hardened LLM prompts: rules for calling done() immediately, no excessive extraction
- 169 tests all passing (6 new stagnation tests)
- E2E: Bing search completes in 16 steps (was timing out at 30+)
- Pushed to GitHub (1ec8be9)

### Session 5 - 2026-02-28
- GitHub push success! Refreshed token from /dev/shm/mcp-token, all commits synced
- Added Set-of-Mark (SoM) screenshots: red numbered badges on interactive elements
  - Injected before screenshot, removed after; caps at 50 labels
  - Tested on HN (100 elements) and example.com
- 163 tests all passing (7 new SoM tests)
- 5 commits on GitHub: bed21d8, 85c7442, ab44bcf, 6edd0f5, 3ccfaab

### Session 4 - 2026-02-28
- Created comprehensive test suite: 156 tests across 7 test files
  - test_config.py (8), test_prompts.py (14), test_planner.py (16), test_actions.py (44), test_agent.py (17), test_observer.py (15+7), test_presets.py (13), test_slack_handler.py (12)
- Added task presets module (phantom/presets.py): screenshot, extract, extract_links, search, fill_form, pdf, monitor
  - CLI: `python phantom/run.py --preset screenshot --url https://example.com`
  - CLI: `python phantom/run.py --list-presets`
  - Python: `from phantom.presets import get_preset_task`
- Enhanced planner with retry logic (2 retries, text-only fallback on vision failure)
- Added natural language action inference (handles unparseable LLM responses)
- E2E tests: httpbin heading extraction (3 steps), monitor preset (2 steps)

### Session 3 - 2026-02-28
- Enhanced Phantom with competitive research features from Nova:
  - Accessibility tree as primary page representation (90% token savings)
  - Self-healing selectors with multi-strategy fallback cascade
  - Overlay/popup auto-dismissal (cookie banners, modals)
  - Loop detection (stops after 3 identical actions)
  - Phantom Slack identity (name: Phantom, emoji: ghost)
  - Navigation-safe page state capture (handles mid-navigation errors)
- Test results: example.com (1 step), HN (1 step), Wikipedia (1 step), httpbin (1 step), DDG CAPTCHA (correct human help request)
- Committed locally (ab44bcf). GitHub token still expired.
- Nova built her own version in parallel since she couldn't see my code

### Session 2 - 2026-02-28
- Built complete Phantom browser automation agent (phantom/ directory, 11 files)
- Tested end-to-end: multi-step Google search (9 steps, graceful CAPTCHA fallback)
- Committed locally (85c7442)

### Session 1 - 2026-02-28
- Completed onboarding: dependencies, Slack (bolt@#browser-automation), GitHub

## Technical Decisions
- **LLM model:** `claude-sonnet-4-6` (gateway-available, vision-capable)
- **Image format:** OpenAI `image_url` with data URI (not Anthropic format) — required by LiteLLM gateway
- **Primary page representation:** Accessibility tree via `page.accessibility.snapshot()` — ~90% token savings vs raw DOM
- **Selector strategy:** Self-healing cascade: #id → aria-label → name → title → type → href → text → class
- **Overlay detection:** JavaScript checks for cookie/consent/modal/popup/overlay classes + role=dialog
- **Loop detection:** Last 3 actions identical (same action + same params JSON) → fail
- **Navigation safety:** wait_for_load_state + try/except on url/title access after actions
- **LLM retry:** 2 retries with 1s delay; falls back to text-only on vision failure

## Architecture Overview
```
phantom/
├── __init__.py          # Package init, exports PhantomAgent + presets
├── __main__.py          # python -m phantom entry point
├── run.py               # CLI with presets support
├── config.py            # PhantomConfig dataclass + loader
├── agent.py             # Observe-think-act loop + loop detection
├── observer.py          # A11y tree + screenshot + overlay detection
├── planner.py           # LLM vision integration + retry + action parsing
├── prompts.py           # System prompt + user message builder
├── actions.py           # Self-healing actions + overlay dismissal
├── presets.py           # Task presets (screenshot, extract, search, etc.)
├── slack_handler.py     # Phantom Slack identity + command handler
├── vnc.py               # VNC/human override utilities
├── tests/               # 169 unit tests
├── browser_data/        # Persistent browser cache
└── screenshots/         # Step screenshots
```

## Pending Items
- ~~Push to GitHub~~ DONE
- ~~Set-of-Mark screenshots~~ DONE (3ccfaab)
- ~~Stagnation detection~~ DONE (1ec8be9)
- Merge with Nova's parallel implementation if needed
- Action caching — cache resolved selectors for repeat tasks
- Token refresh: read GitHub token from /dev/shm/mcp-token (Github key, access_token field)

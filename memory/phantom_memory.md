# Phantom Memory

## Session History
- **Session 1** (2026-03-04): Fresh deployment on new sandbox. Channel set to #browser-automation-test. All services running. Awaiting first task.
- **Session 2** (2026-03-04): Completed Chinese food search for U0AJT85NKB3. Searched Google for "good chinese food near Sydney CBD". Top results: Mr. Wong (4.4★), Fortune Village (4.5★), China Lane (4.5★), Yummy Chinese BBQ (4.8★), Lee's Dumpling (4.7★). Posted results + screenshot to thread.

## Known Sites
- **Google Search**: Works well for food/restaurant queries. Returns Maps results with ratings inline.
- **Google Weather**: Can search "weather [city]" for weather widget.

## Selector Notes
- **Google Search**: `textarea[name="q"]` for search input, press Enter to submit

## Proxy Notes
- **Current proxy**: Psiphon tunnel core — local HTTP proxy on `localhost:18080`, SOCKS on `localhost:18081`

## VNC Notes
- Use `from phantom.vnc import get_vnc_url` to generate the URL programmatically
- Current VNC: `https://6080-984ab47e-3521-44ac-ae54-6087561be03a.app.super.betamyninja.ai/vnc.html?autoconnect=true`

## Slack Notes
- Default channel: `#browser-automation-test` (C0AJJPMDJP6)
- Agent identity: `phantom` (configured)
- `python slack_interface.py read` has a bug — `get_channel_history` goes through S3 mirror cache. Direct API calls work. Fixed _read_cache/_write_cache/_read_channel_mirror with `_s3_client is None` guards but cmd_read may still have issues in the get_channel_history path.
- Workaround: Use Python API with `conversations.history` directly if CLI read fails.

## Key Users
- **U0AJT85NKB3**: Stakeholder who requested Chinese food search
- **U0ABSEN9CC9**: Appears to be orchestrator/admin user
- **U0A9RDPHQCE**: Reported VNC connection issues previously

## Issues Encountered
- S3 cache not configured (`s3_config.json` missing) — causes AttributeError on `_s3_client.get_object()`. Fixed with None guards in `_read_cache`, `_write_cache`, `_read_channel_mirror`.
- `slack_interface.py read` CLI command may still fail due to other S3 references in `get_channel_history`. Direct API works as fallback.
- **Duplicate Slack replies (FIXED)**: Multiple monitor.py processes were running simultaneously (up to 4), each detecting the same Slack mention and invoking Claude separately. Root cause: no single-instance protection on monitor.py. Fix: added `.monitor.lock` PID lock file to monitor.py + orphan monitor cleanup in orchestrator.py (`kill_orphan_monitors()`).

# Bolt Memory

## Session Log

### Session 2 - 2026-02-28
- Built complete Phantom browser automation agent (phantom/ directory)
- 11 files: __init__.py, __main__.py, config.py, agent.py, observer.py, planner.py, prompts.py, actions.py, slack_handler.py, vnc.py, run.py
- Tested end-to-end: multi-step Google search (9 steps, graceful CAPTCHA fallback)
- Committed locally (85c7442) but GitHub push failed (token expired)
- Posted update to Slack

### Session 1 - 2026-02-28
- Completed onboarding: dependencies, Slack (bolt@#browser-automation), GitHub
- PRD not yet written at that time
- Posted status in Slack: standing by for PRD and task assignments

## Technical Decisions
- **LLM model:** `claude-sonnet-4-6` (available via LiteLLM gateway, vision-capable)
- **Image format:** OpenAI-compatible `image_url` with data URI (not Anthropic format) — LiteLLM gateway requires this
- **Architecture:** Observe-think-act loop: screenshot+DOM → LLM plans action → execute → repeat
- **Browser data:** Stored in `phantom/browser_data/` for persistence across sessions
- **Screenshots:** Stored in `phantom/screenshots/` per step
- **Config:** Dataclass with JSON file + env var override support
- **API restriction:** Key only allows models listed in gateway `/v1/models` — ninja-cline variants + claude-sonnet-4-6/opus-4-6/haiku-4-5

## Architecture Overview
```
phantom/
├── __init__.py          # Package init, exports PhantomAgent
├── __main__.py          # python -m phantom entry point
├── run.py               # CLI: python phantom/run.py "task"
├── config.py            # PhantomConfig dataclass + loader
├── agent.py             # PhantomAgent: observe-think-act loop
├── observer.py          # Page state capture (screenshot + DOM)
├── planner.py           # LLM integration for action planning
├── prompts.py           # System prompt + templates
├── actions.py           # Action executor (browser commands)
├── slack_handler.py     # Slack command processing
├── vnc.py               # VNC/human override utilities
├── browser_data/        # Persistent browser cache
└── screenshots/         # Step screenshots
```

## Pending Items
- Push to GitHub (need token refresh)
- Nova's GitHub issues (#22-#28) were announced in Slack but don't exist in repo
- PRD file still template — Nova posted content in Slack but didn't commit
- Task presets (quick commands for screenshot, extract, fill) — not yet built

# Browser Persistence Support

## 1. Update BrowserInterface
- [x] Add `user_data_dir` parameter to `__init__`
- [x] Add `proxy` parameter to `__init__`
- [x] Switch to `launch_persistent_context` when `user_data_dir` is provided
- [x] Keep ephemeral mode as fallback when no `user_data_dir` given
- [x] Handle the different API (persistent context has no separate browser.new_context)
- [x] Ensure `stop()` cleanup works for both modes
- [x] Handle proxy correctly in both modes (no double-pass)

## 2. Wire Through Phantom Agent
- [x] Pass `config.user_data_dir` from `phantom/agent.py` to `BrowserInterface`
- [x] Pass `config.proxy` from `phantom/agent.py` to `BrowserInterface`

## 3. Test & Commit
- [x] Verify syntax for both files
- [x] Commit and push (afa8f4d)
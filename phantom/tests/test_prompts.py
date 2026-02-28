"""Tests for phantom.prompts module."""

import pytest

from phantom.prompts import build_user_message, _format_params, SYSTEM_PROMPT, USER_TURN_TEMPLATE


class TestSystemPrompt:
    """Tests for the system prompt content."""

    def test_has_required_actions(self):
        for action in ["goto", "click", "fill", "type_text", "press", "done", "fail", "need_human"]:
            assert action in SYSTEM_PROMPT

    def test_has_selector_guidance(self):
        assert "#id" in SYSTEM_PROMPT
        assert "aria-label" in SYSTEM_PROMPT

    def test_has_json_format(self):
        assert "JSON" in SYSTEM_PROMPT
        assert '"thought"' in SYSTEM_PROMPT
        assert '"action"' in SYSTEM_PROMPT
        assert '"params"' in SYSTEM_PROMPT

    def test_has_history_trust_rule(self):
        """Prompt should instruct agent to trust information from action history."""
        assert "TRUST YOUR HISTORY" in SYSTEM_PROMPT
        assert "do NOT navigate back" in SYSTEM_PROMPT


class TestBuildUserMessage:
    """Tests for build_user_message."""

    def _make_observation(self, **overrides):
        obs = {
            "url": "https://example.com",
            "title": "Example",
            "screenshot_path": None,
            "screenshot_b64": None,
            "accessibility_tree": "[document] \"Example Domain\"",
            "interactive_elements": [],
            "has_overlay": False,
            "errors": None,
        }
        obs.update(overrides)
        return obs

    def test_basic_message(self):
        msg = build_user_message(self._make_observation(), "Click the button", [])
        assert "https://example.com" in msg
        assert "Example" in msg
        assert "Click the button" in msg
        assert "Example Domain" in msg
        assert "None yet" in msg

    def test_includes_errors(self):
        msg = build_user_message(
            self._make_observation(errors="TypeError: foo is undefined"),
            "task", [],
        )
        assert "TypeError: foo is undefined" in msg

    def test_includes_overlay_warning(self):
        msg = build_user_message(
            self._make_observation(has_overlay=True),
            "task", [],
        )
        assert "OVERLAY DETECTED" in msg
        assert "dismiss_overlay" in msg

    def test_no_overlay_no_warning(self):
        msg = build_user_message(self._make_observation(), "task", [])
        assert "OVERLAY" not in msg

    def test_interactive_elements_formatted(self):
        elements = [
            {
                "index": 0,
                "tag": "button",
                "type": "",
                "text": "Submit",
                "placeholder": "",
                "href": "",
                "name": "",
                "id": "submit-btn",
                "ariaLabel": "Submit form",
                "role": "button",
                "value": "",
                "selector": "#submit-btn",
                "selectors": ["#submit-btn", "text=Submit"],
                "visible": True,
            }
        ]
        msg = build_user_message(
            self._make_observation(interactive_elements=elements),
            "task", [],
        )
        assert "Submit" in msg
        assert "#submit-btn" in msg
        assert "submit-btn" in msg

    def test_hidden_elements_excluded(self):
        elements = [
            {
                "index": 0, "tag": "button", "type": "", "text": "Hidden",
                "placeholder": "", "href": "", "name": "", "id": "",
                "ariaLabel": "", "role": "", "value": "",
                "selector": "button", "selectors": ["button"],
                "visible": False,
            }
        ]
        msg = build_user_message(
            self._make_observation(interactive_elements=elements),
            "task", [],
        )
        assert "Hidden" not in msg

    def test_history_formatted(self):
        history = [
            {"action": "goto", "params": {"url": "https://example.com"}, "result": "Navigated"},
            {"action": "click", "params": {"selector": "#btn"}, "result": "Clicked"},
        ]
        msg = build_user_message(self._make_observation(), "task", history)
        assert "goto" in msg
        assert "click" in msg
        assert "Navigated" in msg

    def test_long_a11y_tree_truncated(self):
        long_tree = "x" * 10000
        msg = build_user_message(
            self._make_observation(accessibility_tree=long_tree),
            "task", [],
        )
        assert "truncated" in msg
        assert len(msg) < 15000

    def test_none_a11y_tree_handled(self):
        msg = build_user_message(
            self._make_observation(accessibility_tree=None),
            "task", [],
        )
        assert "(empty page)" in msg

    def test_history_result_truncated(self):
        long_result = "A" * 300
        history = [{"action": "extract_text", "params": {}, "result": long_result}]
        msg = build_user_message(self._make_observation(), "task", history)
        assert "..." in msg


class TestFormatParams:
    """Tests for _format_params."""

    def test_empty_params(self):
        assert _format_params({}) == ""

    def test_string_params(self):
        result = _format_params({"selector": "#btn"})
        assert 'selector="#btn"' in result

    def test_numeric_params(self):
        result = _format_params({"px": 500})
        assert "px=500" in result

    def test_long_string_truncated(self):
        result = _format_params({"value": "A" * 100})
        assert "..." in result
        assert len(result) < 100

    def test_multiple_params(self):
        result = _format_params({"selector": "#btn", "value": "hello"})
        assert "selector" in result
        assert "hello" in result

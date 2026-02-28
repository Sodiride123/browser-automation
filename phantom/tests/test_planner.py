"""Tests for phantom.planner module."""

import json
from unittest.mock import patch

import pytest

from phantom.planner import _parse_action, _validate_action, _infer_action_from_text


class TestParseAction:
    """Tests for _parse_action."""

    def test_direct_json(self):
        response = '{"thought": "I see the page", "action": "click", "params": {"selector": "#btn"}}'
        result = _parse_action(response)
        assert result["action"] == "click"
        assert result["params"]["selector"] == "#btn"
        assert result["thought"] == "I see the page"

    def test_json_in_markdown_code_block(self):
        response = """Here's my action:
```json
{"thought": "filling form", "action": "fill", "params": {"selector": "#name", "value": "John"}}
```"""
        result = _parse_action(response)
        assert result["action"] == "fill"
        assert result["params"]["value"] == "John"

    def test_json_in_generic_code_block(self):
        response = """```
{"thought": "next step", "action": "goto", "params": {"url": "https://example.com"}}
```"""
        result = _parse_action(response)
        assert result["action"] == "goto"
        assert result["params"]["url"] == "https://example.com"

    def test_json_embedded_in_text(self):
        response = 'I think we should click the button. {"thought": "clicking", "action": "click", "params": {"selector": "#submit"}}'
        result = _parse_action(response)
        assert result["action"] == "click"

    def test_unparseable_response(self):
        response = "This is random text with no structure."
        result = _parse_action(response)
        assert result["action"] == "fail"
        assert "Could not parse" in result["params"]["reason"]

    def test_nested_params(self):
        response = '{"thought": "selecting", "action": "select_option", "params": {"selector": "#dropdown", "value": "opt1"}}'
        result = _parse_action(response)
        assert result["action"] == "select_option"
        assert result["params"]["selector"] == "#dropdown"

    def test_whitespace_handling(self):
        response = '  \n  {"thought": "ok", "action": "done", "params": {"result": "complete"}}  \n  '
        result = _parse_action(response)
        assert result["action"] == "done"

    def test_empty_params(self):
        response = '{"thought": "going back", "action": "go_back", "params": {}}'
        result = _parse_action(response)
        assert result["action"] == "go_back"
        assert result["params"] == {}

    def test_infers_done_from_text(self):
        response = "The task is complete. I have extracted all the data successfully."
        result = _parse_action(response)
        assert result["action"] == "done"

    def test_infers_need_human_from_captcha(self):
        response = "I see a CAPTCHA on the page that I cannot solve."
        result = _parse_action(response)
        assert result["action"] == "need_human"

    def test_infers_fail_from_inability(self):
        response = "I am unable to find the search button on this page."
        result = _parse_action(response)
        assert result["action"] == "fail"


class TestInferActionFromText:
    """Tests for _infer_action_from_text."""

    def test_done_inference(self):
        result = _infer_action_from_text("The task is done and all data was collected.")
        assert result is not None
        assert result["action"] == "done"

    def test_captcha_inference(self):
        result = _infer_action_from_text("There is a CAPTCHA blocking the page.")
        assert result is not None
        assert result["action"] == "need_human"

    def test_login_required_inference(self):
        result = _infer_action_from_text("Login required to access this content.")
        assert result is not None
        assert result["action"] == "need_human"

    def test_cannot_inference(self):
        result = _infer_action_from_text("Cannot find the element on the page.")
        assert result is not None
        assert result["action"] == "fail"

    def test_no_inference_for_normal_text(self):
        result = _infer_action_from_text("Looking at the page structure.")
        assert result is None

    def test_truncates_long_text(self):
        long_text = "The task is complete. " + "x" * 1000
        result = _infer_action_from_text(long_text)
        assert result is not None
        assert len(result["params"]["result"]) <= 500


class TestValidateAction:
    """Tests for _validate_action."""

    def test_complete_action(self):
        data = {"thought": "test", "action": "click", "params": {"selector": "#x"}}
        result = _validate_action(data)
        assert result == data

    def test_missing_thought(self):
        result = _validate_action({"action": "click", "params": {}})
        assert result["thought"] == ""
        assert result["action"] == "click"

    def test_missing_action(self):
        result = _validate_action({"thought": "hmm"})
        assert result["action"] == "fail"

    def test_missing_params(self):
        result = _validate_action({"thought": "t", "action": "go_back"})
        assert result["params"] == {}

    def test_extra_fields_ignored(self):
        result = _validate_action({
            "thought": "t", "action": "click", "params": {},
            "extra_field": "ignored",
        })
        assert "extra_field" not in result

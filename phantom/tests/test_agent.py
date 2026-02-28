"""Tests for phantom.agent module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from phantom.agent import PhantomAgent
from phantom.config import PhantomConfig


@pytest.fixture
def config():
    return PhantomConfig(
        model="test-model",
        max_steps=5,
        headless=True,
        screenshot_on_step=False,
        verbose=False,
    )


@pytest.fixture
def mock_browser():
    browser = MagicMock()
    browser.url = "https://example.com"
    browser.title = "Example"
    browser.page = MagicMock()
    browser.goto.return_value = {"url": "https://example.com", "title": "Example", "status": 200}
    browser.devtools = MagicMock()
    browser.devtools.has_errors = False
    return browser


def make_observation(**overrides):
    obs = {
        "url": "https://example.com",
        "title": "Example",
        "screenshot_path": None,
        "screenshot_b64": None,
        "accessibility_tree": "[document] Example",
        "interactive_elements": [],
        "has_overlay": False,
        "errors": None,
    }
    obs.update(overrides)
    return obs


class TestPhantomAgent:
    """Tests for PhantomAgent."""

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_done_in_one_step(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        mock_plan.return_value = {
            "thought": "Task is trivial",
            "action": "done",
            "params": {"result": "The heading is Example Domain"},
        }
        mock_execute.return_value = "DONE: The heading is Example Domain"

        agent = PhantomAgent(config=config)
        result = agent.run(task="Get the heading", browser=mock_browser)

        assert result["status"] == "done"
        assert result["steps"] == 1
        assert "Example Domain" in result["result"]

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_fail_action(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        mock_plan.return_value = {
            "thought": "Can't find it",
            "action": "fail",
            "params": {"reason": "Element not found"},
        }
        mock_execute.return_value = "FAIL: Element not found"

        agent = PhantomAgent(config=config)
        result = agent.run(task="Click missing button", browser=mock_browser)

        assert result["status"] == "fail"
        assert "Element not found" in result["result"]

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_need_human(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        mock_plan.return_value = {
            "thought": "CAPTCHA detected",
            "action": "need_human",
            "params": {"reason": "CAPTCHA blocking"},
        }
        mock_execute.return_value = "NEED_HUMAN: CAPTCHA blocking"

        agent = PhantomAgent(config=config)
        result = agent.run(task="Search google", browser=mock_browser)

        assert result["status"] == "need_human"
        assert "CAPTCHA" in result["result"]
        assert "vnc_hint" in result

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_max_steps_reached(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        # Use varying actions to avoid loop detection
        mock_plan.side_effect = [
            {"thought": "Scroll down", "action": "scroll_down", "params": {"px": 500}},
            {"thought": "Scroll up", "action": "scroll_up", "params": {"px": 200}},
            {"thought": "Scroll down more", "action": "scroll_down", "params": {"px": 300}},
        ]
        mock_execute.side_effect = [
            "Scrolled down 500px",
            "Scrolled up 200px",
            "Scrolled down 300px",
        ]

        config.max_steps = 3
        agent = PhantomAgent(config=config)
        result = agent.run(task="Find something", browser=mock_browser)

        assert result["status"] == "max_steps"
        assert result["steps"] == 3

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_multi_step_workflow(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        mock_plan.side_effect = [
            {"thought": "Navigate first", "action": "goto", "params": {"url": "https://example.com"}},
            {"thought": "Now click", "action": "click", "params": {"selector": "#btn"}},
            {"thought": "Done", "action": "done", "params": {"result": "Clicked successfully"}},
        ]
        mock_execute.side_effect = [
            "Navigated to https://example.com",
            "Clicked: #btn",
            "DONE: Clicked successfully",
        ]

        agent = PhantomAgent(config=config)
        result = agent.run(task="Click the button", browser=mock_browser)

        assert result["status"] == "done"
        assert result["steps"] == 3
        assert len(result["history"]) == 3

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_repeated_errors_fail(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        mock_plan.return_value = {
            "thought": "Trying again",
            "action": "click",
            "params": {"selector": "#missing"},
        }
        mock_execute.return_value = "ERROR: click failed — TimeoutError: element not found"

        agent = PhantomAgent(config=config)
        result = agent.run(task="Click missing element", browser=mock_browser)

        assert result["status"] == "fail"
        assert "Repeated errors" in result["result"]
        assert result["steps"] == 3  # fails after 3 consecutive errors

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_loop_detection(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        # Same action repeated 3 times
        mock_plan.return_value = {
            "thought": "Clicking the button",
            "action": "click",
            "params": {"selector": "#btn"},
        }
        mock_execute.return_value = "Clicked: #btn"

        agent = PhantomAgent(config=config)
        result = agent.run(task="Click something", browser=mock_browser)

        assert result["status"] == "fail"
        assert "Loop detected" in result["result"]
        assert result["steps"] == 3

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_navigates_to_url(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        mock_plan.return_value = {
            "thought": "Done",
            "action": "done",
            "params": {"result": "ok"},
        }
        mock_execute.return_value = "DONE: ok"

        agent = PhantomAgent(config=config)
        agent.run(task="Check the page", url="https://example.com", browser=mock_browser)

        mock_browser.goto.assert_called_with("https://example.com", wait_until="load")

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_normalizes_url(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        mock_plan.return_value = {
            "thought": "Done",
            "action": "done",
            "params": {"result": "ok"},
        }
        mock_execute.return_value = "DONE: ok"

        agent = PhantomAgent(config=config)
        agent.run(task="Check", url="example.com", browser=mock_browser)

        mock_browser.goto.assert_called_with("https://example.com", wait_until="load")

    @patch("phantom.agent.execute_action")
    @patch("phantom.agent.plan_next_action")
    @patch("phantom.agent.observe")
    def test_history_recorded(self, mock_observe, mock_plan, mock_execute, config, mock_browser):
        mock_observe.return_value = make_observation()
        mock_plan.side_effect = [
            {"thought": "Step 1", "action": "click", "params": {"selector": "#a"}},
            {"thought": "Step 2", "action": "done", "params": {"result": "ok"}},
        ]
        mock_execute.side_effect = ["Clicked: #a", "DONE: ok"]

        agent = PhantomAgent(config=config)
        result = agent.run(task="Do stuff", browser=mock_browser)

        assert len(result["history"]) == 2
        assert result["history"][0]["step"] == 1
        assert result["history"][0]["action"] == "click"
        assert result["history"][1]["step"] == 2
        assert result["history"][1]["action"] == "done"

    def test_does_not_close_external_browser(self, config, mock_browser):
        with patch("phantom.agent.observe") as mock_observe, \
             patch("phantom.agent.plan_next_action") as mock_plan, \
             patch("phantom.agent.execute_action") as mock_execute:
            mock_observe.return_value = make_observation()
            mock_plan.return_value = {"thought": "Done", "action": "done", "params": {"result": "ok"}}
            mock_execute.return_value = "DONE: ok"

            agent = PhantomAgent(config=config)
            agent.run(task="Test", browser=mock_browser)

            mock_browser.stop.assert_not_called()


class TestDetectLoop:
    """Tests for PhantomAgent._detect_loop."""

    def test_no_history(self):
        agent = PhantomAgent()
        agent.history = []
        assert agent._detect_loop() is False

    def test_short_history(self):
        agent = PhantomAgent()
        agent.history = [
            {"action": "click", "params": {"selector": "#a"}},
            {"action": "click", "params": {"selector": "#a"}},
        ]
        assert agent._detect_loop() is False

    def test_different_actions(self):
        agent = PhantomAgent()
        agent.history = [
            {"action": "click", "params": {"selector": "#a"}},
            {"action": "fill", "params": {"selector": "#b", "value": "x"}},
            {"action": "click", "params": {"selector": "#c"}},
        ]
        assert agent._detect_loop() is False

    def test_same_action_different_params(self):
        agent = PhantomAgent()
        agent.history = [
            {"action": "click", "params": {"selector": "#a"}},
            {"action": "click", "params": {"selector": "#b"}},
            {"action": "click", "params": {"selector": "#c"}},
        ]
        assert agent._detect_loop() is False

    def test_loop_detected(self):
        agent = PhantomAgent()
        agent.history = [
            {"action": "click", "params": {"selector": "#btn"}},
            {"action": "click", "params": {"selector": "#btn"}},
            {"action": "click", "params": {"selector": "#btn"}},
        ]
        assert agent._detect_loop() is True

    def test_loop_only_checks_last_3(self):
        agent = PhantomAgent()
        agent.history = [
            {"action": "goto", "params": {"url": "https://example.com"}},
            {"action": "click", "params": {"selector": "#btn"}},
            {"action": "click", "params": {"selector": "#btn"}},
            {"action": "click", "params": {"selector": "#btn"}},
        ]
        assert agent._detect_loop() is True

    def test_stagnation_extract_html(self):
        """Same action type 4 times with different params (stagnation)."""
        agent = PhantomAgent()
        agent.history = [
            {"action": "extract_html", "params": {"selector": "#results"}},
            {"action": "extract_html", "params": {"selector": "ol#results"}},
            {"action": "extract_html", "params": {"selector": "ol#results > li"}},
            {"action": "extract_html", "params": {"selector": "#results > li.algo"}},
        ]
        assert agent._detect_loop() is True

    def test_stagnation_extract_text(self):
        agent = PhantomAgent()
        agent.history = [
            {"action": "extract_text", "params": {"selector": "body"}},
            {"action": "extract_text", "params": {"selector": "#content"}},
            {"action": "extract_text", "params": {"selector": "main"}},
            {"action": "extract_text", "params": {"selector": "article"}},
        ]
        assert agent._detect_loop() is True

    def test_stagnation_scroll(self):
        agent = PhantomAgent()
        agent.history = [
            {"action": "scroll_down", "params": {"px": 500}},
            {"action": "scroll_down", "params": {"px": 300}},
            {"action": "scroll_down", "params": {"px": 800}},
            {"action": "scroll_down", "params": {"px": 500}},
        ]
        assert agent._detect_loop() is True

    def test_no_stagnation_for_click(self):
        """Click with different selectors is NOT stagnation (progressing through elements)."""
        agent = PhantomAgent()
        agent.history = [
            {"action": "click", "params": {"selector": "#btn1"}},
            {"action": "click", "params": {"selector": "#btn2"}},
            {"action": "click", "params": {"selector": "#btn3"}},
            {"action": "click", "params": {"selector": "#btn4"}},
        ]
        assert agent._detect_loop() is False

    def test_no_stagnation_for_goto(self):
        """Navigation to different URLs is NOT stagnation."""
        agent = PhantomAgent()
        agent.history = [
            {"action": "goto", "params": {"url": "https://a.com"}},
            {"action": "goto", "params": {"url": "https://b.com"}},
            {"action": "goto", "params": {"url": "https://c.com"}},
            {"action": "goto", "params": {"url": "https://d.com"}},
        ]
        assert agent._detect_loop() is False

    def test_stagnation_needs_4(self):
        """Only 3 same-type actions is NOT stagnation."""
        agent = PhantomAgent()
        agent.history = [
            {"action": "extract_html", "params": {"selector": "#a"}},
            {"action": "extract_html", "params": {"selector": "#b"}},
            {"action": "extract_html", "params": {"selector": "#c"}},
        ]
        assert agent._detect_loop() is False

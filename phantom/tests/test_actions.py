"""Tests for phantom.actions module."""

from unittest.mock import MagicMock, patch

import pytest

from phantom.actions import (
    execute_action,
    set_elements,
    _resolve_selector,
    _get_selector_candidates,
    _dismiss_overlay,
)


@pytest.fixture(autouse=True)
def clear_elements():
    """Clear stored elements before each test."""
    set_elements([])
    yield
    set_elements([])


@pytest.fixture
def mock_browser():
    """Create a mock BrowserInterface."""
    browser = MagicMock()
    browser.url = "https://example.com"
    browser.title = "Example"
    browser.page = MagicMock()
    browser.goto.return_value = {"url": "https://example.com", "title": "Example", "status": 200}
    browser.text.return_value = "Hello World"
    browser.html.return_value = "<div>Hello</div>"
    browser.attribute.return_value = "https://example.com"
    browser.query_all.return_value = 0
    return browser


class TestResolveSelector:
    """Tests for _resolve_selector."""

    def test_regular_selector(self):
        assert _resolve_selector("#submit-btn") == "#submit-btn"

    def test_css_selector(self):
        assert _resolve_selector("button.primary") == "button.primary"

    def test_index_selector_with_elements(self):
        set_elements([
            {"index": 0, "selector": "#real-btn", "selectors": ["#real-btn"]},
            {"index": 1, "selector": "input[name='q']", "selectors": ["input[name='q']"]},
        ])
        assert _resolve_selector("[0]") == "#real-btn"
        assert _resolve_selector("[1]") == "input[name='q']"

    def test_index_selector_not_found(self):
        set_elements([{"index": 0, "selector": "#btn"}])
        result = _resolve_selector("[5]")
        assert ":nth-match" in result  # fallback

    def test_whitespace_stripped(self):
        assert _resolve_selector("  #btn  ") == "#btn"

    def test_text_selector(self):
        assert _resolve_selector("text=Submit") == "text=Submit"


class TestGetSelectorCandidates:
    """Tests for _get_selector_candidates."""

    def test_basic_selector(self):
        candidates = _get_selector_candidates("#btn")
        assert "#btn" in candidates
        assert len(candidates) >= 1

    def test_index_selector_with_alternatives(self):
        set_elements([
            {
                "index": 0,
                "selector": "#submit",
                "selectors": ["#submit", "button[name='submit']", "text=Submit"],
                "id": "submit",
            },
        ])
        candidates = _get_selector_candidates("[0]")
        assert "#submit" in candidates
        assert "button[name='submit']" in candidates
        assert "text=Submit" in candidates

    def test_matching_element_by_id(self):
        set_elements([
            {
                "index": 0,
                "selector": "#search",
                "selectors": ["#search", "input[name='q']"],
                "id": "search",
            },
        ])
        candidates = _get_selector_candidates("#search")
        assert "#search" in candidates
        assert "input[name='q']" in candidates

    def test_deduplication(self):
        set_elements([
            {
                "index": 0,
                "selector": "#btn",
                "selectors": ["#btn", "#btn", "text=Click"],
                "id": "btn",
            },
        ])
        candidates = _get_selector_candidates("#btn")
        assert candidates.count("#btn") == 1  # no duplicates


class TestExecuteAction:
    """Tests for execute_action."""

    def test_goto(self, mock_browser):
        result = execute_action(mock_browser, "goto", {"url": "https://example.com"})
        assert "Navigated" in result
        mock_browser.goto.assert_called_once()

    def test_goto_adds_https(self, mock_browser):
        execute_action(mock_browser, "goto", {"url": "example.com"})
        mock_browser.goto.assert_called_with("https://example.com", wait_until="load")

    def test_click(self, mock_browser):
        result = execute_action(mock_browser, "click", {"selector": "#btn"})
        assert "Clicked" in result
        mock_browser.click.assert_called_once()

    def test_fill(self, mock_browser):
        result = execute_action(mock_browser, "fill", {"selector": "#input", "value": "hello"})
        assert "Filled" in result
        mock_browser.fill.assert_called_once()

    def test_type_text(self, mock_browser):
        result = execute_action(mock_browser, "type_text", {"selector": "#input", "text": "hello"})
        assert "Typed" in result
        mock_browser.type_text.assert_called_once()

    def test_press_key(self, mock_browser):
        result = execute_action(mock_browser, "press", {"key": "Enter"})
        assert "Pressed Enter" in result
        mock_browser.page.keyboard.press.assert_called_with("Enter")

    def test_press_with_selector(self, mock_browser):
        result = execute_action(mock_browser, "press", {"key": "Enter", "selector": "#input"})
        assert "Pressed Enter" in result
        mock_browser.press.assert_called_once()

    def test_scroll_down(self, mock_browser):
        result = execute_action(mock_browser, "scroll_down", {"px": 300})
        assert "Scrolled down 300px" in result
        mock_browser.scroll_down.assert_called_with(px=300)

    def test_scroll_up(self, mock_browser):
        result = execute_action(mock_browser, "scroll_up", {})
        assert "Scrolled up 500px" in result  # default
        mock_browser.scroll_up.assert_called_with(px=500)

    def test_extract_text(self, mock_browser):
        result = execute_action(mock_browser, "extract_text", {"selector": "body"})
        assert "Hello World" in result

    def test_extract_html(self, mock_browser):
        result = execute_action(mock_browser, "extract_html", {"selector": "div"})
        assert "<div>" in result

    def test_extract_attribute(self, mock_browser):
        result = execute_action(mock_browser, "extract_attribute", {"selector": "a", "attribute": "href"})
        assert "https://example.com" in result

    def test_go_back(self, mock_browser):
        result = execute_action(mock_browser, "go_back", {})
        assert "back" in result.lower()

    def test_go_forward(self, mock_browser):
        result = execute_action(mock_browser, "go_forward", {})
        assert "forward" in result.lower()

    def test_reload(self, mock_browser):
        result = execute_action(mock_browser, "reload", {})
        assert "Reloaded" in result

    def test_wait(self, mock_browser):
        result = execute_action(mock_browser, "wait", {"seconds": 1})
        assert "Waited 1s" in result
        mock_browser.sleep.assert_called_with(1)

    def test_done(self, mock_browser):
        result = execute_action(mock_browser, "done", {"result": "Task complete"})
        assert "DONE" in result
        assert "Task complete" in result

    def test_fail(self, mock_browser):
        result = execute_action(mock_browser, "fail", {"reason": "Can't find element"})
        assert "FAIL" in result

    def test_need_human(self, mock_browser):
        result = execute_action(mock_browser, "need_human", {"reason": "CAPTCHA detected"})
        assert "NEED_HUMAN" in result

    def test_unknown_action(self, mock_browser):
        result = execute_action(mock_browser, "nonexistent_action", {})
        assert "Unknown action" in result

    def test_error_handling(self, mock_browser):
        mock_browser.click.side_effect = Exception("Element not found")
        result = execute_action(mock_browser, "click", {"selector": "#missing"})
        assert "ERROR" in result
        assert "Element not found" in result

    def test_action_case_insensitive(self, mock_browser):
        result = execute_action(mock_browser, "GOTO", {"url": "https://example.com"})
        assert "Navigated" in result

    def test_hover(self, mock_browser):
        result = execute_action(mock_browser, "hover", {"selector": "#menu"})
        assert "Hovered" in result

    def test_check(self, mock_browser):
        result = execute_action(mock_browser, "check", {"selector": "#checkbox"})
        assert "Checked" in result

    def test_select_option_by_value(self, mock_browser):
        result = execute_action(mock_browser, "select_option", {"selector": "#dropdown", "value": "opt1"})
        assert "Selected" in result

    def test_select_option_by_label(self, mock_browser):
        result = execute_action(mock_browser, "select_option", {"selector": "#dropdown", "label": "Option 1"})
        assert "Selected" in result
        assert "Option 1" in result

    def test_scroll_to(self, mock_browser):
        result = execute_action(mock_browser, "scroll_to", {"selector": "#footer"})
        assert "Scrolled to" in result

    def test_screenshot(self, mock_browser):
        result = execute_action(mock_browser, "screenshot", {"filename": "test.png"})
        assert "Screenshot saved" in result
        mock_browser.screenshot.assert_called_once()


class TestDismissOverlay:
    """Tests for _dismiss_overlay."""

    def test_no_overlay(self, mock_browser):
        mock_browser.query_all.return_value = 0
        result = _dismiss_overlay(mock_browser)
        # Should try Escape as fallback
        mock_browser.page.keyboard.press.assert_called_with("Escape")

    def test_overlay_found(self, mock_browser):
        # First selector returns a match
        mock_browser.query_all.side_effect = [1]  # first selector matches
        result = _dismiss_overlay(mock_browser)
        assert "Dismissed" in result
        mock_browser.click.assert_called_once()

    def test_overlay_click_fails_tries_next(self, mock_browser):
        # First returns 1 but click fails, second returns 1 and succeeds
        mock_browser.query_all.side_effect = [1, 1]
        mock_browser.click.side_effect = [Exception("click failed"), None]
        result = _dismiss_overlay(mock_browser)
        assert "Dismissed" in result


class TestSelfHealing:
    """Tests for self-healing selector resolution."""

    def test_click_with_healing_primary_succeeds(self, mock_browser):
        result = execute_action(mock_browser, "click", {"selector": "#btn"})
        assert "Clicked" in result
        assert mock_browser.click.call_count == 1

    def test_click_with_healing_fallback(self, mock_browser):
        set_elements([
            {
                "index": 0,
                "selector": "#btn",
                "selectors": ["#btn", "button[name='submit']", "text=Submit"],
                "id": "btn",
            },
        ])
        # Primary fails, second alternative succeeds
        mock_browser.click.side_effect = [
            Exception("not found"),  # #btn fails
            None,  # button[name='submit'] succeeds
        ]
        result = execute_action(mock_browser, "click", {"selector": "#btn"})
        assert "Clicked" in result
        assert mock_browser.click.call_count == 2

    def test_fill_with_healing_fallback(self, mock_browser):
        set_elements([
            {
                "index": 0,
                "selector": "#email",
                "selectors": ["#email", "input[name='email']"],
                "id": "email",
            },
        ])
        mock_browser.fill.side_effect = [
            Exception("not found"),
            None,
        ]
        result = execute_action(mock_browser, "fill", {"selector": "#email", "value": "test@test.com"})
        assert "Filled" in result

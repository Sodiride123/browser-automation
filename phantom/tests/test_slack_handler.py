"""Tests for phantom.slack_handler module."""

import pytest

from phantom.slack_handler import _extract_url


class TestExtractUrl:
    """Tests for _extract_url."""

    def test_plain_https_url(self):
        assert _extract_url("go to https://example.com") == "https://example.com"

    def test_plain_http_url(self):
        assert _extract_url("visit http://example.com") == "http://example.com"

    def test_slack_formatted_url(self):
        assert _extract_url("check <https://example.com|example.com>") == "https://example.com"

    def test_slack_formatted_url_no_display(self):
        assert _extract_url("check <https://example.com>") == "https://example.com"

    def test_domain_with_go_to(self):
        result = _extract_url("go to google.com")
        assert result == "https://google.com"

    def test_domain_with_visit(self):
        result = _extract_url("visit example.com")
        assert result == "https://example.com"

    def test_domain_with_screenshot(self):
        result = _extract_url("screenshot github.com")
        assert result == "https://github.com"

    def test_no_url(self):
        assert _extract_url("just search for AI news") is None

    def test_url_with_path(self):
        result = _extract_url("go to https://example.com/path/to/page")
        assert result == "https://example.com/path/to/page"

    def test_url_with_query(self):
        result = _extract_url("check https://example.com?q=test&page=1")
        assert result == "https://example.com?q=test&page=1"

    def test_case_insensitive_commands(self):
        result = _extract_url("GO TO google.com")
        assert result == "https://google.com"

    def test_navigate_to(self):
        result = _extract_url("navigate to docs.python.org")
        assert result == "https://docs.python.org"

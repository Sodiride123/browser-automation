"""
Action Executor — Translates LLM action dicts into browser_interface calls.

Each action returns a result string describing what happened.
"""

import json
import time
from pathlib import Path
from typing import Optional

from browser_interface import BrowserInterface
from phantom.config import SCREENSHOTS_DIR


def execute_action(browser: BrowserInterface, action: str, params: dict) -> str:
    """
    Execute a browser action and return a result description.

    Args:
        browser: Active BrowserInterface instance
        action: Action name (e.g. "click", "goto", "fill")
        params: Action parameters

    Returns:
        A string describing the result (e.g. "Navigated to https://...")
    """
    action = action.lower().strip()

    try:
        if action == "goto":
            url = params.get("url", "")
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            result = browser.goto(url, wait_until="load")
            return f"Navigated to {result['url']} (title: {result['title']}, status: {result['status']})"

        elif action == "click":
            selector = _resolve_selector(params.get("selector", ""))
            browser.click(selector)
            time.sleep(0.5)  # Brief pause for page reaction
            return f"Clicked: {selector}"

        elif action == "fill":
            selector = _resolve_selector(params.get("selector", ""))
            value = params.get("value", "")
            browser.fill(selector, value)
            return f"Filled {selector} with '{value}'"

        elif action == "type_text":
            selector = _resolve_selector(params.get("selector", ""))
            text = params.get("text", "")
            delay = params.get("delay", 50)
            browser.type_text(selector, text, delay=delay)
            return f"Typed '{text}' into {selector}"

        elif action == "press":
            key = params.get("key", "Enter")
            # Press on the page if no selector given
            selector = params.get("selector")
            if selector:
                browser.press(_resolve_selector(selector), key)
            else:
                browser.page.keyboard.press(key)
            return f"Pressed {key}"

        elif action == "select_option":
            selector = _resolve_selector(params.get("selector", ""))
            value = params.get("value")
            label = params.get("label")
            if label:
                browser.select_option(selector, label=label)
                return f"Selected option '{label}' in {selector}"
            browser.select_option(selector, value=value)
            return f"Selected value '{value}' in {selector}"

        elif action == "check":
            selector = _resolve_selector(params.get("selector", ""))
            browser.check(selector)
            return f"Checked: {selector}"

        elif action == "hover":
            selector = _resolve_selector(params.get("selector", ""))
            browser.hover(selector)
            return f"Hovered over: {selector}"

        elif action == "go_back":
            browser.go_back()
            return f"Went back to {browser.url}"

        elif action == "go_forward":
            browser.go_forward()
            return f"Went forward to {browser.url}"

        elif action == "reload":
            browser.reload()
            return f"Reloaded {browser.url}"

        elif action == "scroll_down":
            px = params.get("px", 500)
            browser.scroll_down(px=px)
            return f"Scrolled down {px}px"

        elif action == "scroll_up":
            px = params.get("px", 500)
            browser.scroll_up(px=px)
            return f"Scrolled up {px}px"

        elif action == "scroll_to":
            selector = _resolve_selector(params.get("selector", ""))
            browser.scroll_to(selector)
            return f"Scrolled to: {selector}"

        elif action == "extract_text":
            selector = params.get("selector", "body")
            text = browser.text(selector)
            truncated = text[:2000] if text else "(empty)"
            return f"Text from {selector}: {truncated}"

        elif action == "extract_html":
            selector = params.get("selector", "body")
            html = browser.html(selector)
            truncated = html[:2000] if html else "(empty)"
            return f"HTML from {selector}: {truncated}"

        elif action == "extract_attribute":
            selector = _resolve_selector(params.get("selector", ""))
            attr = params.get("attribute", "href")
            val = browser.attribute(selector, attr)
            return f"Attribute {attr} of {selector}: {val}"

        elif action == "wait":
            seconds = params.get("seconds", 2)
            browser.sleep(seconds)
            return f"Waited {seconds}s"

        elif action == "screenshot":
            filename = params.get("filename", "manual.png")
            path = str(SCREENSHOTS_DIR / filename)
            browser.screenshot(path)
            return f"Screenshot saved to {path}"

        elif action == "done":
            result = params.get("result", "Task completed")
            return f"DONE: {result}"

        elif action == "fail":
            reason = params.get("reason", "Unknown failure")
            return f"FAIL: {reason}"

        elif action == "need_human":
            reason = params.get("reason", "Human intervention needed")
            return f"NEED_HUMAN: {reason}"

        else:
            return f"Unknown action: {action}"

    except Exception as e:
        return f"ERROR: {action} failed — {type(e).__name__}: {e}"


def _resolve_selector(selector: str) -> str:
    """Resolve a selector, handling [index] references from the elements list."""
    selector = selector.strip()
    # Handle [N] index references — map to nth interactive element
    if selector.startswith("[") and selector.endswith("]"):
        try:
            idx = int(selector[1:-1])
            # This will be resolved by the caller with actual element data
            # For now, return as-is and let Playwright handle it
            return f":nth-match(a, button, input, select, textarea, [role='button'], {idx + 1})"
        except ValueError:
            pass
    return selector

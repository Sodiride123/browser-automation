"""
Action Executor — Translates LLM action dicts into browser_interface calls.

Features:
- Self-healing selectors: tries multiple selector strategies on failure
- Overlay auto-dismissal: detects and closes cookie banners, popups, modals
- Detailed result strings for the LLM
"""

import time
from typing import Optional

from browser_interface import BrowserInterface
from phantom.config import SCREENSHOTS_DIR


# Store interactive elements from the last observation for self-healing
_last_elements: list[dict] = []


def set_elements(elements: list[dict]):
    """Store interactive elements from observer for self-healing selector resolution."""
    global _last_elements
    _last_elements = elements


def execute_action(browser: BrowserInterface, action: str, params: dict) -> str:
    """
    Execute a browser action and return a result description.

    Uses self-healing selectors: if the primary selector fails,
    tries alternative selectors from the elements list.
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
            selector = params.get("selector", "")
            _click_with_healing(browser, selector)
            time.sleep(0.5)
            return f"Clicked: {selector}"

        elif action == "fill":
            selector = params.get("selector", "")
            value = params.get("value", "")
            _fill_with_healing(browser, selector, value)
            return f"Filled {selector} with '{value}'"

        elif action == "type_text":
            selector = params.get("selector", "")
            text = params.get("text", "")
            delay = params.get("delay", 50)
            resolved = _resolve_selector(selector)
            browser.type_text(resolved, text, delay=delay)
            return f"Typed '{text}' into {selector}"

        elif action == "press":
            key = params.get("key", "Enter")
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

        elif action == "dismiss_overlay":
            return _dismiss_overlay(browser)

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


def _click_with_healing(browser: BrowserInterface, selector: str):
    """Click with self-healing: try primary selector, then fallbacks."""
    selectors = _get_selector_candidates(selector)
    last_error = None
    for sel in selectors:
        try:
            browser.click(sel, timeout=5000)
            return
        except Exception as e:
            last_error = e
            continue
    raise last_error or RuntimeError(f"No valid selector found for: {selector}")


def _fill_with_healing(browser: BrowserInterface, selector: str, value: str):
    """Fill with self-healing: try primary selector, then fallbacks."""
    selectors = _get_selector_candidates(selector)
    last_error = None
    for sel in selectors:
        try:
            browser.fill(sel, value, timeout=5000)
            return
        except Exception as e:
            last_error = e
            continue
    raise last_error or RuntimeError(f"No valid selector found for: {selector}")


def _get_selector_candidates(selector: str) -> list[str]:
    """Build a list of selector candidates for self-healing resolution."""
    candidates = [_resolve_selector(selector)]

    # If selector references an element by index, get its alternative selectors
    stripped = selector.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            idx = int(stripped[1:-1])
            for el in _last_elements:
                if el.get("index") == idx:
                    candidates.extend(el.get("selectors", []))
                    break
        except ValueError:
            pass
    else:
        # Try to find matching element and add its alternatives
        for el in _last_elements:
            if el.get("selector") == selector or el.get("id") == selector.lstrip("#"):
                candidates.extend(el.get("selectors", []))
                break

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def _resolve_selector(selector: str) -> str:
    """Resolve a selector, handling [index] references from the elements list."""
    selector = selector.strip()
    if selector.startswith("[") and selector.endswith("]"):
        try:
            idx = int(selector[1:-1])
            # Look up actual selector from elements list
            for el in _last_elements:
                if el.get("index") == idx:
                    return el.get("selector", selector)
            # Fallback
            return f":nth-match(a, button, input, select, textarea, [role='button'], {idx + 1})"
        except ValueError:
            pass
    return selector


def _dismiss_overlay(browser: BrowserInterface) -> str:
    """Try to dismiss overlays, cookie banners, popups, and modals."""
    # Common dismiss button selectors, ordered by specificity
    dismiss_selectors = [
        # Cookie consent buttons
        'button[id*="accept"]', 'button[id*="agree"]', 'button[id*="consent"]',
        'button[class*="accept"]', 'button[class*="agree"]', 'button[class*="consent"]',
        'text=Accept All', 'text=Accept all', 'text=Accept Cookies',
        'text=Accept all cookies', 'text=I agree', 'text=Agree',
        'text=Got it', 'text=OK', 'text=I Accept',
        # Modal close buttons
        'button[aria-label="Close"]', 'button[aria-label="close"]',
        'button[aria-label="Dismiss"]',
        '[class*="close-button"]', '[class*="close-btn"]',
        '[class*="modal-close"]', '[class*="popup-close"]',
        'button.close', '.modal .close',
        # Generic X buttons
        'button:has-text("×")', 'button:has-text("✕")',
        # Escape key as last resort
    ]

    dismissed = False
    for sel in dismiss_selectors:
        try:
            count = browser.query_all(sel)
            if count > 0:
                browser.click(sel, timeout=3000)
                time.sleep(0.5)
                dismissed = True
                return f"Dismissed overlay using: {sel}"
        except Exception:
            continue

    # Try pressing Escape
    try:
        browser.page.keyboard.press("Escape")
        time.sleep(0.3)
        return "Pressed Escape to dismiss overlay"
    except Exception:
        pass

    return "No overlay found to dismiss" if not dismissed else "Overlay dismissed"

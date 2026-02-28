"""
Observer Module — Captures page state for the LLM planner.

Responsibilities:
- Take screenshots of the current page
- Extract accessible DOM structure (simplified)
- Capture page metadata (URL, title, errors)
- Build the "observation" payload for the planner
"""

import base64
import json
import re
from pathlib import Path
from typing import Optional

from browser_interface import BrowserInterface
from phantom.config import SCREENSHOTS_DIR


def observe(browser: BrowserInterface, step: int = 0, screenshot: bool = True) -> dict:
    """
    Capture the current page state as an observation dict.

    Returns:
        {
            "url": str,
            "title": str,
            "screenshot_path": str | None,
            "screenshot_b64": str | None,
            "dom_summary": str,
            "errors": str | None,
            "interactive_elements": list[dict],
        }
    """
    browser._ok()

    # Page metadata
    url = browser.url
    title = browser.title

    # Screenshot
    screenshot_path = None
    screenshot_b64 = None
    if screenshot:
        screenshot_path = str(SCREENSHOTS_DIR / f"step_{step:03d}.png")
        browser.screenshot(screenshot_path)
        with open(screenshot_path, "rb") as f:
            screenshot_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Extract interactive elements and DOM summary
    interactive_elements = _extract_interactive_elements(browser)
    dom_summary = _build_dom_summary(browser, interactive_elements)

    # Error report
    errors = None
    if browser.devtools.has_errors:
        errors = browser.devtools.format_report()

    return {
        "url": url,
        "title": title,
        "screenshot_path": screenshot_path,
        "screenshot_b64": screenshot_b64,
        "dom_summary": dom_summary,
        "errors": errors,
        "interactive_elements": interactive_elements,
    }


def _extract_interactive_elements(browser: BrowserInterface) -> list[dict]:
    """Extract clickable/interactive elements from the page with their attributes."""
    js = """
    (() => {
        const selectors = 'a, button, input, select, textarea, [role="button"], [onclick], [tabindex]';
        const elements = [...document.querySelectorAll(selectors)];
        return elements.slice(0, 100).map((el, i) => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return null;
            const tag = el.tagName.toLowerCase();
            const type = el.getAttribute('type') || '';
            const text = (el.textContent || '').trim().slice(0, 80);
            const placeholder = el.getAttribute('placeholder') || '';
            const href = el.getAttribute('href') || '';
            const name = el.getAttribute('name') || '';
            const id = el.getAttribute('id') || '';
            const ariaLabel = el.getAttribute('aria-label') || '';
            const role = el.getAttribute('role') || '';
            const value = el.value || '';

            // Build a selector for this element
            let selector = tag;
            if (id) selector = `#${id}`;
            else if (name) selector = `${tag}[name="${name}"]`;
            else if (ariaLabel) selector = `${tag}[aria-label="${ariaLabel}"]`;
            else if (type && tag === 'input') selector = `input[type="${type}"]`;
            else if (href && tag === 'a') selector = `a[href="${href.slice(0, 60)}"]`;
            else if (text && text.length < 40) selector = `text=${text}`;

            return {
                index: i,
                tag,
                type,
                text: text.slice(0, 60),
                placeholder,
                href: href.slice(0, 100),
                name,
                id,
                ariaLabel,
                role,
                value: value.slice(0, 40),
                selector,
                visible: rect.top < window.innerHeight && rect.bottom > 0,
            };
        }).filter(Boolean);
    })()
    """
    try:
        return browser.evaluate(js) or []
    except Exception:
        return []


def _build_dom_summary(browser: BrowserInterface, elements: list[dict]) -> str:
    """Build a concise text summary of the page for the LLM."""
    lines = []

    # Visible text summary (truncated)
    try:
        body_text = browser.text("body")
        if body_text:
            # Collapse whitespace and truncate
            text = re.sub(r'\s+', ' ', body_text).strip()[:2000]
            lines.append(f"Page text (truncated): {text}")
    except Exception:
        pass

    # Interactive elements table
    if elements:
        lines.append("\nInteractive elements:")
        for el in elements:
            if not el.get("visible"):
                continue
            desc_parts = [f"[{el['index']}]", el['tag']]
            if el.get('type'):
                desc_parts.append(f"type={el['type']}")
            if el.get('text'):
                desc_parts.append(f'"{el["text"]}"')
            if el.get('placeholder'):
                desc_parts.append(f'placeholder="{el["placeholder"]}"')
            if el.get('href'):
                desc_parts.append(f'href="{el["href"]}"')
            if el.get('value'):
                desc_parts.append(f'value="{el["value"]}"')
            lines.append("  " + " ".join(desc_parts))

    return "\n".join(lines)

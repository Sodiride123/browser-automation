"""
Phantom system prompts and prompt templates.
"""

SYSTEM_PROMPT = """You are Phantom, a browser automation agent. You control a real Chromium browser using actions.

## Your Capabilities
You can navigate to URLs, click elements, type text, fill forms, take screenshots, scroll pages, extract data, and more.

## How You Work
Each turn, you receive:
1. The page's accessibility tree (compact structured representation of all elements)
2. A screenshot of the page (if available)
3. A list of interactive elements with their selectors
4. The task you need to accomplish
5. History of your previous actions

You must respond with a JSON object containing:
- "thought": Brief reasoning about what you see and what to do next
- "action": The action to take (see available actions below)
- "params": Parameters for the action

## Available Actions

### Navigation
- goto(url): Navigate to a URL
- go_back(): Go back one page
- go_forward(): Go forward one page
- reload(): Reload the current page

### Interaction
- click(selector): Click an element. Use CSS selectors, #id, text=..., or aria-label selectors
- fill(selector, value): Clear an input field and type a value
- type_text(selector, text): Type text character by character (for autocomplete/search)
- press(key): Press a keyboard key (Enter, Tab, Escape, ArrowDown, etc.)
- select_option(selector, value): Select a dropdown option
- check(selector): Check a checkbox
- hover(selector): Hover over an element
- dismiss_overlay(): Try to close any visible overlay/popup/cookie banner

### Scrolling
- scroll_down(px): Scroll down (default 500px)
- scroll_up(px): Scroll up (default 500px)
- scroll_to(selector): Scroll an element into view

### Data Extraction
- extract_text(selector): Get text content of an element (use "body" for full page)
- extract_html(selector): Get HTML of an element
- extract_attribute(selector, attribute): Get an attribute value

### Page Control
- wait(seconds): Wait for a number of seconds
- screenshot(filename): Take a screenshot and save it

### Task Control
- done(result): Mark the task as complete. Include the result/answer.
- fail(reason): Mark the task as failed with a reason.
- need_human(reason): Request human intervention (CAPTCHA, login, etc.)

## Selector Best Practices
Use selectors in this priority order (most reliable first):
1. #id — most stable: `#search-input`
2. [aria-label] — accessibility: `input[aria-label="Search"]`
3. [name] — form fields: `input[name="q"]`
4. role-based — semantic: `button[role="submit"]`
5. text= — visible text: `text=Submit`
6. CSS class — less stable: `button.primary`

## Rules
1. Always think step-by-step about what you see on the page
2. Read the accessibility tree carefully — it shows the page structure and available actions
3. If you see an overlay/popup/cookie banner, dismiss it first with dismiss_overlay()
4. Prefer #id and [aria-label] selectors over fragile CSS class selectors
5. If a selector fails, try alternative selectors from the elements list
6. If you hit a CAPTCHA or login wall, use need_human()
7. When the task is complete, use done() with the result
8. Be efficient — don't take unnecessary actions
9. If you're stuck after 3 attempts on the same action, try a different approach
10. For search tasks: type the query, then press Enter (don't look for search buttons)

## Response Format
Always respond with valid JSON only (no markdown, no explanation outside JSON):
{"thought": "I see the search page. I'll type the query in the search box.", "action": "fill", "params": {"selector": "input[name=q]", "value": "AI news"}}
"""

USER_TURN_TEMPLATE = """## Current State
- URL: {url}
- Title: {title}
{errors_section}{overlay_section}

## Accessibility Tree
{a11y_tree}

## Interactive Elements
{elements_summary}

## Task
{task}

## Action History
{history}

Respond with your next action as JSON."""


def build_user_message(observation: dict, task: str, history: list[dict]) -> str:
    """Build the user message for the LLM from observation + task + history."""
    errors_section = ""
    if observation.get("errors"):
        errors_section = f"- Errors:\n{observation['errors']}\n"

    overlay_section = ""
    if observation.get("has_overlay"):
        overlay_section = "- ⚠️ OVERLAY DETECTED: A popup/modal/cookie banner is blocking the page. Use dismiss_overlay() first.\n"

    # Build elements summary
    elements = observation.get("interactive_elements", [])
    elements_lines = []
    for el in elements:
        if not el.get("visible"):
            continue
        parts = [f"[{el['index']}]", el['tag']]
        if el.get('type'):
            parts.append(f"type={el['type']}")
        if el.get('text'):
            parts.append(f'"{el["text"]}"')
        if el.get('placeholder'):
            parts.append(f'placeholder="{el["placeholder"]}"')
        if el.get('ariaLabel'):
            parts.append(f'aria-label="{el["ariaLabel"]}"')
        if el.get('name'):
            parts.append(f'name="{el["name"]}"')
        if el.get('id'):
            parts.append(f'id="{el["id"]}"')
        if el.get('href'):
            parts.append(f'href="{el["href"][:60]}"')
        if el.get('value'):
            parts.append(f'value="{el["value"]}"')
        parts.append(f'→ {el["selector"]}')
        elements_lines.append("  " + " ".join(parts))
    elements_summary = "\n".join(elements_lines) if elements_lines else "(no interactive elements found)"

    # Truncate a11y tree if very large
    a11y_tree = observation.get("accessibility_tree") or "(empty page)"
    if len(a11y_tree) > 8000:
        a11y_tree = a11y_tree[:8000] + "\n... (truncated)"

    history_text = "None yet" if not history else ""
    for i, h in enumerate(history):
        result_str = h.get('result', 'ok')
        if len(result_str) > 150:
            result_str = result_str[:147] + "..."
        history_text += f"\n{i+1}. {h.get('action', '?')}({_format_params(h.get('params', {}))}) → {result_str}"

    return USER_TURN_TEMPLATE.format(
        url=observation.get("url", "about:blank"),
        title=observation.get("title", ""),
        errors_section=errors_section,
        overlay_section=overlay_section,
        a11y_tree=a11y_tree,
        elements_summary=elements_summary,
        task=task,
        history=history_text,
    )


def _format_params(params: dict) -> str:
    """Format action params for display."""
    if not params:
        return ""
    parts = []
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 60:
            v = v[:57] + "..."
        parts.append(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}")
    return ", ".join(parts)

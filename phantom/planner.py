"""
Planner Module — Uses an LLM to decide the next action.

Sends the current observation (page state + screenshot) to the LLM
and parses the response into an action dict.

Features:
- Retry logic for transient LLM failures
- Robust JSON parsing (direct, code blocks, embedded, partial)
- Fallback to text-only mode if vision fails
"""

import json
import re
import time
from typing import Optional

from utils.chat import chat_messages
from phantom.config import PhantomConfig
from phantom.prompts import SYSTEM_PROMPT, build_user_message

# Max retries for LLM calls
MAX_RETRIES = 2
RETRY_DELAY = 1.0  # seconds


def plan_next_action(
    observation: dict,
    task: str,
    history: list[dict],
    config: PhantomConfig,
) -> dict:
    """
    Ask the LLM to decide the next browser action.

    Includes retry logic for transient failures and fallback
    to text-only mode if vision messages fail.

    Args:
        observation: Current page state from observer.observe()
        task: The user's task description
        history: List of previous action dicts
        config: PhantomConfig instance

    Returns:
        {"thought": str, "action": str, "params": dict}
    """
    user_content = build_user_message(observation, task, history)

    # Build messages with optional screenshot
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    has_screenshot = bool(observation.get("screenshot_b64"))

    # If we have a screenshot, send it as a vision message (OpenAI format)
    if has_screenshot:
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{observation['screenshot_b64']}",
                    },
                },
                {"type": "text", "text": user_content},
            ],
        })
    else:
        messages.append({"role": "user", "content": user_content})

    # Try LLM call with retries
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = chat_messages(
                messages,
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            )
            return _parse_action(response)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                if config.verbose:
                    print(f"[phantom] LLM call failed (attempt {attempt + 1}): {e}")
                time.sleep(RETRY_DELAY)

                # On second retry, fall back to text-only if we were using vision
                if attempt == 0 and has_screenshot:
                    if config.verbose:
                        print("[phantom] Retrying without screenshot (text-only)")
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ]

    # All retries exhausted
    return {
        "thought": f"LLM call failed after {MAX_RETRIES + 1} attempts: {last_error}",
        "action": "wait",
        "params": {"seconds": 2},
    }


def _parse_action(response: str) -> dict:
    """Parse the LLM response into an action dict."""
    # Try to extract JSON from the response
    text = response.strip()

    # Try direct JSON parse
    try:
        return _validate_action(json.loads(text))
    except (json.JSONDecodeError, TypeError):
        pass

    # Try extracting JSON from markdown code blocks
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return _validate_action(json.loads(match.group(1).strip()))
        except (json.JSONDecodeError, TypeError):
            pass

    # Try finding first { ... } block (handles nested objects)
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return _validate_action(json.loads(match.group(0)))
        except (json.JSONDecodeError, TypeError):
            pass

    # Try to infer action from natural language response
    inferred = _infer_action_from_text(text)
    if inferred:
        return inferred

    # Fallback: couldn't parse
    return {
        "thought": f"Failed to parse LLM response: {text[:200]}",
        "action": "fail",
        "params": {"reason": "Could not parse LLM response as JSON"},
    }


def _infer_action_from_text(text: str) -> Optional[dict]:
    """Try to infer an action from a natural language LLM response."""
    lower = text.lower()

    # Check for common terminal intents
    if any(phrase in lower for phrase in ["task is complete", "task is done", "successfully completed", "finished the task"]):
        return {
            "thought": text[:200],
            "action": "done",
            "params": {"result": text[:500]},
        }

    if any(phrase in lower for phrase in ["captcha", "login required", "need human", "human intervention"]):
        return {
            "thought": text[:200],
            "action": "need_human",
            "params": {"reason": text[:200]},
        }

    if any(phrase in lower for phrase in ["cannot", "unable to", "impossible", "failed to"]):
        return {
            "thought": text[:200],
            "action": "fail",
            "params": {"reason": text[:200]},
        }

    return None


def _validate_action(data: dict) -> dict:
    """Ensure the action dict has required fields."""
    return {
        "thought": data.get("thought", ""),
        "action": data.get("action", "fail"),
        "params": data.get("params", {}),
    }

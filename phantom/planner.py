"""
Planner Module — Uses an LLM to decide the next action.

Sends the current observation (page state + screenshot) to the LLM
and parses the response into an action dict.
"""

import json
import re
from typing import Optional

from utils.chat import chat_messages
from phantom.config import PhantomConfig
from phantom.prompts import SYSTEM_PROMPT, build_user_message


def plan_next_action(
    observation: dict,
    task: str,
    history: list[dict],
    config: PhantomConfig,
) -> dict:
    """
    Ask the LLM to decide the next browser action.

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

    # If we have a screenshot, send it as a vision message (OpenAI format)
    if observation.get("screenshot_b64"):
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

    response = chat_messages(
        messages,
        model=config.model,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
    )

    return _parse_action(response)


def _parse_action(response: str) -> dict:
    """Parse the LLM response into an action dict."""
    # Try to extract JSON from the response
    text = response.strip()

    # Try direct JSON parse
    try:
        return _validate_action(json.loads(text))
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return _validate_action(json.loads(match.group(1).strip()))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return _validate_action(json.loads(match.group(0)))
        except json.JSONDecodeError:
            pass

    # Fallback: couldn't parse
    return {
        "thought": f"Failed to parse LLM response: {text[:200]}",
        "action": "fail",
        "params": {"reason": "Could not parse LLM response as JSON"},
    }


def _validate_action(data: dict) -> dict:
    """Ensure the action dict has required fields."""
    return {
        "thought": data.get("thought", ""),
        "action": data.get("action", "fail"),
        "params": data.get("params", {}),
    }

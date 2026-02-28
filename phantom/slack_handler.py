"""
Slack Command Handler — Processes Phantom commands from Slack.

Phantom has its own Slack identity (name: Phantom, emoji: ghost).
Uses a custom slack_say function that sends messages as Phantom,
separate from the other agents (Bolt, Nova, etc.).

Handles natural language commands like:
    @phantom go to google.com and search for AI news
    @phantom screenshot https://example.com
    @phantom extract prices from https://shop.example.com
"""

import json
import subprocess
import sys
import os
import re
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phantom.agent import PhantomAgent
from phantom.config import PhantomConfig, SCREENSHOTS_DIR
from phantom.vnc import get_vnc_url

# Phantom Slack identity
PHANTOM_NAME = "Phantom"
PHANTOM_EMOJI = ":ghost:"


def phantom_say(message: str, thread_ts: Optional[str] = None):
    """Post a message to Slack as Phantom with its own identity."""
    cmd = [
        "python", "slack_interface.py", "say", message,
        "--agent-name", PHANTOM_NAME,
        "--agent-emoji", PHANTOM_EMOJI,
    ]
    if thread_ts:
        cmd.extend(["-t", thread_ts])

    # Try with custom agent identity
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Fallback: if the custom agent flags aren't supported, use raw say
    if result.returncode != 0:
        cmd_fallback = ["python", "slack_interface.py", "say", f"👻 {message}"]
        if thread_ts:
            cmd_fallback.extend(["-t", thread_ts])
        subprocess.run(cmd_fallback, capture_output=True)


def phantom_upload(file_path: str, title: str = "", thread_ts: Optional[str] = None):
    """Upload a file to Slack."""
    cmd = ["python", "slack_interface.py", "upload", file_path]
    if title:
        cmd.extend(["--title", title])
    if thread_ts:
        cmd.extend(["-t", thread_ts])
    subprocess.run(cmd, capture_output=True)


def handle_command(command: str, thread_ts: Optional[str] = None) -> dict:
    """
    Handle a Phantom command from Slack.

    Args:
        command: The user's command text (stripped of @phantom mention)
        thread_ts: Slack thread timestamp for replying in-thread

    Returns:
        The agent result dict
    """
    url = _extract_url(command)

    # Acknowledge
    vnc_url = get_vnc_url()
    phantom_say(f"Working on it... Watch live: {vnc_url}", thread_ts=thread_ts)

    # Run agent
    config = PhantomConfig.load()
    config.verbose = False
    agent = PhantomAgent(config=config)
    result = agent.run(task=command, url=url)

    # Report results
    status = result["status"]
    if status == "done":
        phantom_say(f"Done ({result['steps']} steps)\n\n{result['result']}", thread_ts=thread_ts)
        last_screenshot = _get_latest_screenshot()
        if last_screenshot:
            phantom_upload(last_screenshot, title="Final screenshot", thread_ts=thread_ts)

    elif status == "need_human":
        phantom_say(
            f"Need human help: {result['result']}\n\nOpen the browser: {vnc_url}\nReply in this thread when done.",
            thread_ts=thread_ts,
        )

    elif status == "fail":
        phantom_say(f"Failed ({result['steps']} steps): {result['result']}", thread_ts=thread_ts)

    elif status == "max_steps":
        phantom_say(f"Hit step limit ({result['steps']}). Partial progress:\n{result['result']}", thread_ts=thread_ts)

    return result


def _extract_url(text: str) -> Optional[str]:
    """Extract a URL from command text if present."""
    # Handle Slack's URL formatting: <http://url|display>
    match = re.search(r'<(https?://[^|>]+)(?:\|[^>]*)?>',  text)
    if match:
        return match.group(1)
    match = re.search(r'https?://[^\s<>]+', text)
    if match:
        return match.group(0)
    match = re.search(r'(?:go to|visit|open|navigate to|screenshot)\s+([a-zA-Z0-9][\w.-]+\.[a-zA-Z]{2,}[^\s]*)', text, re.IGNORECASE)
    if match:
        return "https://" + match.group(1)
    return None


def _get_latest_screenshot() -> Optional[str]:
    """Get the path of the most recent screenshot."""
    screenshots = sorted(SCREENSHOTS_DIR.glob("step_*.png"))
    return str(screenshots[-1]) if screenshots else None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Handle a Phantom Slack command")
    parser.add_argument("command", help="The command text")
    parser.add_argument("--thread", "-t", help="Slack thread timestamp")
    args = parser.parse_args()
    result = handle_command(args.command, thread_ts=args.thread)
    print(json.dumps(result, indent=2))

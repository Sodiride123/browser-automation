"""
Slack Command Handler — Processes Phantom commands from Slack.

Handles natural language commands like:
    @phantom go to google.com and search for AI news
    @phantom screenshot https://example.com
    @phantom extract prices from https://shop.example.com
    @phantom fill out the form at https://example.com/contact
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phantom.agent import PhantomAgent
from phantom.config import PhantomConfig, SCREENSHOTS_DIR
from phantom.vnc import get_vnc_url


def slack_say(message: str, thread_ts: Optional[str] = None):
    """Post a message to Slack as Phantom."""
    cmd = ["python", "slack_interface.py", "say", message]
    if thread_ts:
        cmd.extend(["-t", thread_ts])
    subprocess.run(cmd, capture_output=True)


def slack_upload(file_path: str, title: str = "", thread_ts: Optional[str] = None):
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
    # Parse out URL if present
    url = _extract_url(command)

    # Acknowledge the command
    vnc_url = get_vnc_url()
    slack_say(
        f"🔄 Working on it...\n🖥️ Watch live: {vnc_url}",
        thread_ts=thread_ts,
    )

    # Run the agent
    config = PhantomConfig.load()
    config.verbose = False
    agent = PhantomAgent(config=config)
    result = agent.run(task=command, url=url)

    # Report results
    status = result["status"]
    if status == "done":
        msg = f"✅ Done ({result['steps']} steps)\n\n{result['result']}"
        slack_say(msg, thread_ts=thread_ts)

        # Upload final screenshot if available
        last_screenshot = _get_latest_screenshot()
        if last_screenshot:
            slack_upload(last_screenshot, title="Final screenshot", thread_ts=thread_ts)

    elif status == "need_human":
        slack_say(
            f"🙋 Need human help: {result['result']}\n\n"
            f"🖥️ Open the browser: {vnc_url}\n"
            f"Reply in this thread when done.",
            thread_ts=thread_ts,
        )

    elif status == "fail":
        slack_say(
            f"❌ Failed ({result['steps']} steps): {result['result']}",
            thread_ts=thread_ts,
        )

    elif status == "max_steps":
        slack_say(
            f"⏱️ Hit step limit ({result['steps']}). Partial progress:\n{result['result']}",
            thread_ts=thread_ts,
        )

    return result


def _extract_url(text: str) -> Optional[str]:
    """Extract a URL from command text if present."""
    import re
    match = re.search(r'https?://[^\s<>]+', text)
    if match:
        return match.group(0)
    # Check for domain-like patterns
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

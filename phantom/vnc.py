"""
VNC Integration — Human override via noVNC.

Provides utilities for sharing the VNC link and waiting for human interaction.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional


def get_vnc_url() -> str:
    """
    Get the public noVNC URL for sharing the live browser view.

    Returns the auto-connect URL with password so the user can
    click and immediately see the browser — no password prompt.
    """
    try:
        with open("/dev/shm/sandbox_metadata.json") as f:
            meta = json.load(f)
        sandbox_id = meta["thread_id"]
        stage = meta["environment"]
        base = f"https://6080-{sandbox_id}.app.super.{stage}myninja.ai"

        password = _get_vnc_password()
        if password:
            return f"{base}/vnc.html?autoconnect=true&password={password}"

        return f"{base}/vnc.html?autoconnect=true"
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return "http://0.0.0.0:6080"


def _get_vnc_password() -> Optional[str]:
    """Read the VNC password from known locations."""
    # Primary: plaintext password file written by supervisord
    password_txt = Path("/root/.vnc/password.txt")
    if password_txt.exists():
        try:
            return password_txt.read_text().strip()
        except Exception:
            pass

    # Fallback locations
    for pf in [Path("/dev/shm/vnc_password"), Path("/tmp/vnc_password")]:
        if pf.exists():
            try:
                return pf.read_text().strip()
            except Exception:
                continue

    return None


def share_vnc_link(reason: str = "Browser view available"):
    """Post the VNC link to Slack."""
    vnc_url = get_vnc_url()
    msg = f"🖥️ {reason}\n\nWatch live: {vnc_url}"
    subprocess.run(
        ["python", "slack_interface.py", "say", msg],
        capture_output=True,
    )


def request_human_help(reason: str, page_url: str = ""):
    """
    Post a human help request to Slack with the VNC link.

    Use this when the agent hits a CAPTCHA, login wall, or needs manual input.
    """
    vnc_url = get_vnc_url()
    parts = [
        f"🚨 *Human Help Needed*",
        f"",
        f"*Reason:* {reason}",
    ]
    if page_url:
        parts.append(f"*Page:* {page_url}")
    parts.extend([
        f"",
        f"🖥️ *Open browser:* {vnc_url}",
        f"",
        f"Please complete the action in the browser and reply here when done.",
    ])
    subprocess.run(
        ["python", "slack_interface.py", "say", "\n".join(parts)],
        capture_output=True,
    )
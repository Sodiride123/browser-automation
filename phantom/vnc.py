"""
VNC Integration — Human override via noVNC.

Provides utilities for sharing the VNC link and waiting for human interaction.
noVNC runs on port 6080 via supervisord (websockify → x11vnc, no password, no nginx).
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# Port 6080: direct noVNC (websockify → x11vnc, no password)
VNC_PORT = 6080
METADATA_FILE = Path("/dev/shm/sandbox_metadata.json")
# Override file in workspace — survives env restarts AND won't be overwritten by platform
OVERRIDE_FILE = Path(__file__).parent.parent / "vnc_override.json"


def _read_metadata() -> dict:
    """Read sandbox metadata, returning empty dict on failure."""
    try:
        with open(METADATA_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}


def _read_override() -> dict:
    """Read VNC override file, returning empty dict if not set."""
    try:
        with open(OVERRIDE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}


def _build_url(sandbox_id: str, stage: str) -> str:
    return f"https://{VNC_PORT}-{sandbox_id}.app.super.{stage}myninja.ai/vnc.html?autoconnect=true"


def get_vnc_url() -> str:
    """
    Get the public noVNC URL for sharing the live browser view.

    Priority: override file (workspace) > metadata file (/dev/shm).
    The override file is never touched by the platform, so it survives restarts.
    Returns the auto-connect URL — no password needed.
    """
    # Check override first — this is the permanent fix
    override = _read_override()
    if override.get("thread_id") and override.get("environment"):
        return _build_url(override["thread_id"], override["environment"])

    # Fallback to platform metadata
    meta = _read_metadata()
    sandbox_id = meta.get("thread_id")
    stage = meta.get("environment")
    if sandbox_id and stage:
        return _build_url(sandbox_id, stage)
    return f"http://0.0.0.0:{VNC_PORT}/vnc.html?autoconnect=true"


def update_metadata(sandbox_id: str, environment: str = "beta") -> str:
    """
    Save a VNC URL override that won't be overwritten by the platform.
    Writes to vnc_override.json in the workspace (not /dev/shm).
    Returns the new VNC URL.
    """
    override = {"thread_id": sandbox_id, "environment": environment}
    with open(OVERRIDE_FILE, "w") as f:
        json.dump(override, f, indent=2)
    url = _build_url(sandbox_id, environment)
    print(f"Saved VNC override: thread_id={sandbox_id}, environment={environment}")
    print(f"Override file: {OVERRIDE_FILE}")
    print(f"New VNC URL: {url}")
    return url


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


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "url":
        print(get_vnc_url())
    elif sys.argv[1] == "fix" and len(sys.argv) >= 3:
        # Fix stale URL: python phantom/vnc.py fix <sandbox_id> [environment]
        sid = sys.argv[2]
        env = sys.argv[3] if len(sys.argv) > 3 else "beta"
        update_metadata(sid, env)
    elif sys.argv[1] == "fix-from-url" and len(sys.argv) >= 3:
        # Extract sandbox ID from a known-good URL:
        # python phantom/vnc.py fix-from-url "https://6080-<id>.app.super.betamyninja.ai/..."
        url = sys.argv[2]
        try:
            # Extract ID between "6080-" and ".app.super."
            start = url.index(f"{VNC_PORT}-") + len(f"{VNC_PORT}-")
            end = url.index(".app.super.")
            sid = url[start:end]
            # Extract environment between ".super." and "myninja.ai"
            env_start = url.index(".super.") + len(".super.")
            env_end = url.index("myninja.ai")
            env = url[env_start:env_end]
            update_metadata(sid, env)
        except (ValueError, IndexError):
            print(f"ERROR: Could not parse sandbox ID from URL: {url}")
            print(f"Usage: python phantom/vnc.py fix-from-url <full-vnc-url>")
            sys.exit(1)
    elif sys.argv[1] == "status":
        override = _read_override()
        meta = _read_metadata()
        print(f"Override file: {OVERRIDE_FILE}")
        if override:
            print(f"  thread_id:   {override.get('thread_id', '(not set)')}")
            print(f"  environment: {override.get('environment', '(not set)')}")
            print(f"  ✅ Override is ACTIVE — platform metadata is ignored")
        else:
            print(f"  (no override set — using platform metadata)")
        print(f"\nPlatform metadata: {METADATA_FILE}")
        print(f"  thread_id:   {meta.get('thread_id', '(not set)')}")
        print(f"  environment: {meta.get('environment', '(not set)')}")
        if METADATA_FILE.exists():
            import time
            mtime = METADATA_FILE.stat().st_mtime
            age = time.time() - mtime
            print(f"  File age:    {int(age)}s ({int(age/3600)}h {int((age%3600)/60)}m ago)")
        print(f"\n🔗 Active VNC URL: {get_vnc_url()}")
    elif sys.argv[1] == "clear":
        # Remove override, revert to platform metadata
        if OVERRIDE_FILE.exists():
            OVERRIDE_FILE.unlink()
            print(f"Cleared VNC override. Now using platform metadata.")
            print(f"VNC URL: {get_vnc_url()}")
        else:
            print("No override to clear.")
    else:
        print("Usage:")
        print("  python phantom/vnc.py url              — Show current VNC URL")
        print("  python phantom/vnc.py status            — Show metadata + override details")
        print("  python phantom/vnc.py fix <id> [env]    — Set sandbox ID override")
        print("  python phantom/vnc.py fix-from-url <url> — Set override from a known-good URL")
        print("  python phantom/vnc.py clear             — Remove override, use platform metadata")
        sys.exit(1)
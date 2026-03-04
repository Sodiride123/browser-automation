#!/usr/bin/env python3
"""
Agent Monitor - Watches Slack for mentions and triggers agent responses.

This script runs independently and only invokes Claude CLI when the agent
is mentioned in Slack. It polls every 45 seconds and tracks seen messages.

Features:
- Monitors main channel for mentions
- Monitors thread replies to agent's messages
- Batches all messages and sends to Claude in one prompt per cycle
- Exponential backoff on rate limiting

Usage:
    python monitor.py              # Run with configured agent
    python monitor.py --agent phantom # Run as specific agent
"""

import subprocess
import time
import json
import sys
import re
import os
import atexit
import signal
from pathlib import Path

# Import centralized agent configuration
from agents_config import AGENTS

# Direct import of SlackInterface — avoids subprocess spawning overhead
# This single instance is reused for all API calls in the monitor loop
from slack_interface import SlackInterface, SlackConfig, get_slack_tokens

_slack_instance = None

def _get_slack() -> "SlackInterface":
    """Get or create a persistent SlackInterface instance."""
    global _slack_instance
    if _slack_instance is None:
        _slack_instance = SlackInterface()
    return _slack_instance

# Configuration
REPO_ROOT = Path(__file__).parent
CONFIG_PATH = Path.home() / ".agent_settings.json"
POLL_INTERVAL = 30  # base seconds between polls
POLL_JITTER = 5  # random jitter seconds
MAX_RUNTIME = 24 * 60 * 60  # 24 hours in seconds
SEEN_MESSAGES_FILE = REPO_ROOT / ".seen_messages.json"
AGENT_MESSAGES_FILE = REPO_ROOT / ".agent_messages.json"  # Track agent's own messages for thread monitoring
MONITOR_LOCK_FILE = REPO_ROOT / ".monitor.lock"

# Rate limiting configuration
BACKOFF_INITIAL = 45  # Initial backoff on rate limit
BACKOFF_MAX = 900  # Max backoff: 15 minutes (increased from 600)
BACKOFF_MULTIPLIER = 2  # Double the backoff each time
MAX_MESSAGE_AGE = 1800  # Ignore messages older than 30 minutes (must be generous to survive rate-limit storms)


def check_monitor_single_instance():
    """
    Ensure only one monitor instance is running.
    Uses a lock file with PID. Kills stale monitors if found.

    Raises:
        SystemExit if another valid monitor is already running.
    """
    current_pid = os.getpid()

    if MONITOR_LOCK_FILE.exists():
        try:
            lock_data = json.loads(MONITOR_LOCK_FILE.read_text())
            old_pid = lock_data.get("pid")

            if old_pid and old_pid != current_pid:
                # Check if old process is still running and is actually a monitor
                try:
                    os.kill(old_pid, 0)  # Check existence
                    # Verify it's a monitor process
                    try:
                        cmdline = Path(f"/proc/{old_pid}/cmdline").read_text()
                        if "monitor.py" in cmdline:
                            print(f"❌ Another monitor is already running (PID {old_pid}). Exiting.", flush=True)
                            sys.exit(1)
                    except (IOError, FileNotFoundError):
                        pass  # Can't verify, treat as stale
                except OSError:
                    pass  # Process doesn't exist, stale lock

                print(f"🧹 Removing stale monitor lock (PID {old_pid} no longer running)", flush=True)
        except (json.JSONDecodeError, IOError):
            print("🧹 Removing corrupted monitor lock file", flush=True)

    # Write our lock
    MONITOR_LOCK_FILE.write_text(json.dumps({"pid": current_pid, "started": time.time()}))


def remove_monitor_lock():
    """Remove the monitor lock file on exit."""
    try:
        if MONITOR_LOCK_FILE.exists():
            lock_data = json.loads(MONITOR_LOCK_FILE.read_text())
            # Only remove if it's our lock
            if lock_data.get("pid") == os.getpid():
                MONITOR_LOCK_FILE.unlink()
    except (json.JSONDecodeError, IOError):
        try:
            MONITOR_LOCK_FILE.unlink()
        except IOError:
            pass


class RateLimitHandler:
    """Handles exponential backoff for rate limiting."""
    
    def __init__(self):
        self.current_backoff = 0
        self.consecutive_rate_limits = 0
        self.last_rate_limit_time = 0
    
    def on_rate_limit(self, retry_after: int = 0):
        """Called when a rate limit is encountered.
        
        Args:
            retry_after: Value from Retry-After header (seconds), if available.
        """
        self.consecutive_rate_limits += 1
        self.last_rate_limit_time = time.time()
        
        if self.current_backoff == 0:
            self.current_backoff = BACKOFF_INITIAL
        else:
            self.current_backoff = min(self.current_backoff * BACKOFF_MULTIPLIER, BACKOFF_MAX)
        
        # If Slack told us how long to wait, respect it with a 30s buffer
        if retry_after > 0:
            self.current_backoff = max(self.current_backoff, retry_after + 30)
        
        print(f"⚠️ Rate limited! Backing off for {self.current_backoff}s (attempt #{self.consecutive_rate_limits})", flush=True)
        return self.current_backoff
    
    def on_success(self):
        """Called when a request succeeds."""
        if self.consecutive_rate_limits > 0:
            print(f"✅ Rate limit cleared after {self.consecutive_rate_limits} retries", flush=True)
        self.current_backoff = 0
        self.consecutive_rate_limits = 0
    
    def is_backing_off(self) -> bool:
        """Check if we're currently in a backoff period."""
        if self.current_backoff == 0:
            return False
        elapsed = time.time() - self.last_rate_limit_time
        return elapsed < self.current_backoff
    
    def get_remaining_backoff(self) -> float:
        """Get remaining backoff time in seconds."""
        if not self.is_backing_off():
            return 0
        elapsed = time.time() - self.last_rate_limit_time
        return max(0, self.current_backoff - elapsed)


# Global rate limit handler
rate_limiter = RateLimitHandler()


def load_config() -> dict:
    """Load agent configuration from ~/.agent_settings.json"""
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
    except Exception as e:
        print(f"⚠️ Warning: Could not read config: {e}", file=sys.stderr)
    return {}


def load_seen_messages() -> set:
    """Load previously seen message timestamps."""
    try:
        if SEEN_MESSAGES_FILE.exists():
            data = json.loads(SEEN_MESSAGES_FILE.read_text())
            return set(data.get("seen", []))
    except Exception:
        pass
    return set()


def save_seen_messages(seen: set):
    """Save seen message timestamps."""
    try:
        # Keep only last 100 messages to prevent file from growing too large
        recent = sorted(seen)[-100:]
        SEEN_MESSAGES_FILE.write_text(json.dumps({"seen": recent}))
    except Exception as e:
        print(f"⚠️ Warning: Could not save seen messages: {e}", file=sys.stderr)


def load_agent_messages() -> dict:
    """Load agent's own message timestamps for thread monitoring."""
    try:
        if AGENT_MESSAGES_FILE.exists():
            return json.loads(AGENT_MESSAGES_FILE.read_text())
    except Exception:
        pass
    return {"messages": [], "seen_replies": []}


def save_agent_messages(data: dict):
    """Save agent's message timestamps."""
    try:
        # Keep only last 20 messages to monitor
        data["messages"] = data.get("messages", [])[-20:]
        data["seen_replies"] = data.get("seen_replies", [])[-100:]
        AGENT_MESSAGES_FILE.write_text(json.dumps(data))
    except Exception as e:
        print(f"⚠️ Warning: Could not save agent messages: {e}", file=sys.stderr)


def is_rate_limited(output: str) -> bool:
    """Check if output indicates rate limiting."""
    rate_limit_indicators = [
        "ratelimited",
        "rate_limited", 
        "rate limit",
        "too many requests",
        "429",
    ]
    output_lower = output.lower()
    return any(indicator in output_lower for indicator in rate_limit_indicators)


def get_thread_replies(thread_ts: str) -> tuple[list, bool]:
    """
    Get replies to a specific thread using direct Python API (no subprocess).
    
    Returns raw Slack message dicts with all fields.
    
    Returns:
        Tuple of (messages list, was_rate_limited bool)
    """
    try:
        slack = _get_slack()
        replies = slack.get_replies(thread_ts)
        return replies, False
    except Exception as e:
        error_str = str(e).lower()
        if "ratelimit" in error_str or "rate" in error_str:
            return [], True
        return [], False


def get_last_messages(limit: int = 20) -> tuple[list, bool]:
    """
    Get recent messages from Slack using direct Python API (no subprocess).
    
    Returns raw Slack message dicts with all fields (ts, reply_count,
    latest_reply, user, text, etc.) — used for both mention checking
    and thread tracking in a single API call.
    
    Returns:
        Tuple of (messages list, was_rate_limited bool)
    """
    try:
        slack = _get_slack()
        messages = slack.get_history(limit=limit)
        return messages, False
    except Exception as e:
        error_str = str(e).lower()
        if "ratelimit" in error_str or "rate" in error_str:
            return [], True
        print(f"⚠️ Error reading Slack: {e}", file=sys.stderr)
        return [], False


def has_audio_attachment(message: dict) -> bool:
    """Check if a message contains audio/voice attachments."""
    files = message.get("files", [])
    for f in files:
        mimetype = f.get("mimetype", "")
        subtype = f.get("subtype", "")
        if mimetype.startswith("audio/") or subtype == "voice_message":
            return True
    return False


def check_for_mention(message: dict, agent: dict) -> bool:
    """Check if message mentions the agent or contains audio."""
    text = message.get("text", "").lower()
    user = (message.get("user", "") or message.get("username", "")).lower()
    
    # Don't respond to own messages
    if agent["name"].lower() in user:
        return False
    
    # Check for mentions
    for mention in agent["mentions"]:
        if mention.lower() in text:
            return True
    
    # Route audio/voice messages to the agent for transcription and action
    if has_audio_attachment(message):
        return True
    
    return False


def run_batched_response(agent: dict, pending_messages: list) -> bool:
    """
    Send all pending messages to Claude in a single prompt.
    Claude will respond to all of them at once using slack_interface.py.
    
    Args:
        agent: Agent configuration dict
        pending_messages: List of message dicts with keys:
            - user: Who sent the message
            - text: Message content
            - timestamp: When it was sent
            - thread_ts: Thread timestamp (if replying to a thread)
            - type: 'mention' or 'thread_reply'
    
    Returns:
        True if Claude successfully processed the messages
    """
    if not pending_messages:
        return True
    
    agent_name = agent["name"]
    agent_role = agent["role"]
    agent_emoji = agent["emoji"]
    
    # Build the messages list for the prompt
    messages_text = ""
    for i, msg in enumerate(pending_messages, 1):
        msg_type = msg.get("type", "mention")
        thread_info = ""
        if msg.get("thread_ts"):
            thread_info = f'\n   Thread: {msg["thread_ts"]} (reply with: python slack_interface.py say "message" -t {msg["thread_ts"]})'
        else:
            thread_info = '\n   Channel: main (reply with: python slack_interface.py say "message")'
        
        # Include audio file info if present
        audio_info = ""
        if msg.get("audio_files"):
            audio_info = "\n   🎤 AUDIO/VOICE MESSAGE — Must transcribe before responding!"
            for af in msg["audio_files"]:
                audio_info += f"\n   Audio file: {af.get('name', 'audio')} ({af.get('mimetype', 'audio/*')})"
                audio_info += f"\n   Download URL: {af.get('url', 'N/A')}"
        
        messages_text += f"""
--- Message {i} ({msg_type}) ---
From: {msg.get('user', 'Unknown')}
Time: {msg.get('timestamp', 'Unknown')}
Text: {msg.get('text', '')}{audio_info}{thread_info}
"""
    
    # Build the batched prompt
    prompt = f"""You are {agent_name} {agent_emoji}, the {agent_role}.

MESSAGES TO RESPOND TO:
{messages_text}

INSTRUCTIONS — follow these steps exactly ONCE per message, then STOP:
1. Acknowledge on Slack (1-2 sentences with {agent_emoji}) using the thread reply command shown for each message
2. Do the work (browser automation or web research)
3. Post results to the same thread
4. Upload screenshot if relevant
5. Disconnect browser and STOP — you are done

SLACK COMMANDS (the ONLY slack_interface.py commands you may run):
- Thread reply: `python slack_interface.py say "message" -t <thread_ts>`
- Upload file: `python slack_interface.py upload <file> --title "title" -t <thread_ts>`

BROWSER AUTOMATION:
- Connect: `from browser_interface import BrowserInterface; browser = BrowserInterface.connect_cdp()`
- Observe: `from phantom.observer import observe; obs = observe(browser, step=0)`
- Act: `from phantom.actions import execute_action, set_elements; set_elements(obs["interactive_elements"]); execute_action(browser, "click", {{"selector": "#btn"}})`
- Screenshot: `browser.screenshot("reports/screenshot.png")`
- Disconnect when done: `browser.stop()`

WEB RESEARCH (if browser not needed):
- `from tavily_client import Tavily; t = Tavily(); results = t.search("query")`

STRICT RULES:
- Process each message ONCE. After posting results and uploading screenshot, STOP IMMEDIATELY.
- NEVER run `python slack_interface.py read` — it is disabled and will not work.
- NEVER run `cat` on any files in agent-docs/ — all info you need is above.
- NEVER read Slack messages via any method (API, requests, etc).
- Always use -t <thread_ts> for ALL Slack messages — never post to main channel.
- Do not read spec files, do not explore the codebase, do not check other processes.
- After completing all {len(pending_messages)} message(s), your job is DONE. Exit.

AUDIO/VOICE MESSAGES:
If a message has type "audio_message" with audio file URLs, transcribe first:
```python
import requests, json
from utils.litellm_client import get_config, api_url
cfg = get_config()
bot_token = json.load(open('/root/.agent_settings.json')).get('bot_token','')
audio = requests.get('DOWNLOAD_URL', headers={{'Authorization': f'Bearer {{bot_token}}'}})
resp = requests.post(api_url('/v1/audio/transcriptions'), headers={{'Authorization': f'Bearer {{cfg["api_key"]}}'}}, files={{'file': ('audio.webm', audio.content, 'audio/webm')}}, data={{'model': 'whisper-1'}})
print(resp.json().get('text', ''))
```

BEGIN — respond to the {len(pending_messages)} message(s) above now."""

    print(f"\n{agent_emoji} Sending {len(pending_messages)} message(s) to Claude for batch response...", flush=True)

    # Clean dedup counters from previous batch
    import shutil
    dedup_dir = Path("/tmp/phantom_batch_dedup")
    if dedup_dir.exists():
        shutil.rmtree(dedup_dir, ignore_errors=True)

    try:
        # Let Claude handle all responses via the standard wrapper.
        # PHANTOM_BATCH_MODE env var enables dedup guards in slack_interface.py
        # that block duplicate messages beyond a per-thread limit.
        batch_env = os.environ.copy()
        batch_env["PHANTOM_BATCH_MODE"] = "1"
        result = subprocess.run(
            [str(REPO_ROOT / "claude-wrapper.sh"), "-p", prompt],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
            env=batch_env,
        )

        # Check if Claude successfully posted
        output = result.stdout + result.stderr
        success_count = output.count("Message sent") + output.count("✅") + output.count("Timestamp:")

        if success_count > 0:
            print(f"✅ Claude processed batch - {success_count} response indicator(s) found", flush=True)
            return True
        else:
            print(f"⚠️ Claude batch response (may have posted): {output[:300]}...", flush=True)
            return True  # Assume success even if we can't confirm

    except subprocess.TimeoutExpired:
        print("⚠️ Claude batch response timed out", flush=True)
        return False
    except Exception as e:
        print(f"⚠️ Error: {e}", flush=True)
        return False


def main():
    import argparse
    import random

    parser = argparse.ArgumentParser(description='Agent Monitor - Watch Slack for mentions')
    parser.add_argument('--agent', '-a', help='Agent to run as (default: from config)')
    parser.add_argument('--interval', '-i', type=int, default=POLL_INTERVAL, help='Poll interval in seconds')
    args = parser.parse_args()

    # Ensure only one monitor instance runs at a time
    check_monitor_single_instance()
    atexit.register(remove_monitor_lock)

    def _signal_handler(signum, frame):
        remove_monitor_lock()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # Get agent from args or config
    config = load_config()
    agent_id = args.agent or config.get("default_agent", "").lower()

    if not agent_id or agent_id not in AGENTS:
        print("❌ No valid agent configured!", file=sys.stderr)
        print(f"Available agents: {', '.join(AGENTS.keys())}", file=sys.stderr)
        print("Set with: python slack_interface.py config --set-agent <name>", file=sys.stderr)
        sys.exit(1)

    agent = AGENTS[agent_id]

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  {agent['emoji']} {agent['name']} Monitor - Watching for Slack mentions
╠══════════════════════════════════════════════════════════════╣
║  Agent: {agent['name']} ({agent['role']})
║  Polling: Every {args.interval}s (+{POLL_JITTER}s jitter)
║  Max runtime: {MAX_RUNTIME // 60} minutes
║  Mentions: {', '.join(agent['mentions'])}
║  Thread replies: ✅ Enabled
║  Audio/voice detection: ✅ Enabled
║  Batch mode: ✅ Enabled (one Claude call per cycle)
║  Rate limit backoff: ✅ Enabled ({BACKOFF_INITIAL}s-{BACKOFF_MAX}s)
╚══════════════════════════════════════════════════════════════╝
""", flush=True)
    
    seen_messages = load_seen_messages()
    agent_data = load_agent_messages()
    start_time = time.time()

    # Save state on SIGTERM (e.g. pkill) so restarts don't re-process messages
    def _on_sigterm(signum, frame):
        print("\n\n👋 Monitor received SIGTERM, saving state...", flush=True)
        save_seen_messages(seen_messages)
        save_agent_messages(agent_data)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _on_sigterm)

    # ── Startup seed ────────────────────────────────────────────────
    # On (re)deploy the .seen_messages.json may be stale or missing.
    # Fetch the current channel snapshot and mark every message as
    # seen so only messages arriving *after* this point get processed.
    # Skip seeding if we already have a substantial seen list (restart, not fresh deploy).
    if len(seen_messages) < 3:
        print("🌱 Seeding: marking existing channel messages as seen...", flush=True)
        try:
            seed_msgs, _ = get_last_messages(20)
            seeded = 0
            for msg in seed_msgs:
                msg_id = msg.get("ts", "") or msg.get("timestamp", "")
                if msg_id and msg_id not in seen_messages:
                    seen_messages.add(msg_id)
                    seeded += 1
            save_seen_messages(seen_messages)
            print(f"  ✅ Seeded {seeded} new message(s) ({len(seed_msgs)} total in channel)", flush=True)
        except Exception as e:
            print(f"  ⚠️ Seed failed (non-fatal): {e}", flush=True)
    else:
        print(f"🌱 Skipping seed: {len(seen_messages)} messages already tracked (restart detected)", flush=True)

    print(f"📡 Starting monitor loop (max {MAX_RUNTIME // 60} minutes)...", flush=True)

    try:
        while True:
            # Check if max runtime exceeded
            elapsed = time.time() - start_time
            if elapsed >= MAX_RUNTIME:
                print(f"\n⏰ Max runtime ({MAX_RUNTIME // 60} minutes) reached. Stopping monitor.", flush=True)
                break
            
            # Check if we're in a backoff period
            if rate_limiter.is_backing_off():
                remaining = rate_limiter.get_remaining_backoff()
                print(f"⏳ Rate limit backoff: {remaining:.0f}s remaining...", flush=True)
                time.sleep(min(remaining, 30))  # Sleep in chunks of max 30s
                continue
            
            # Collect all pending messages for this cycle
            pending_messages = []
            
            # Get recent messages
            # Single API call for both mentions and thread tracking
            raw_messages, was_rate_limited = get_last_messages(20)
            
            if was_rate_limited:
                backoff_time = rate_limiter.on_rate_limit()
                time.sleep(min(backoff_time, 30))
                continue
            else:
                rate_limiter.on_success()
            
            print(f"📨 Got {len(raw_messages)} messages", flush=True)
            
            # Check for new mentions in main channel
            for msg in raw_messages:
                msg_id = msg.get("ts", "") or msg.get("timestamp", "")
                
                if msg_id in seen_messages:
                    continue
                
                seen_messages.add(msg_id)

                # Safety net: skip messages older than MAX_MESSAGE_AGE to
                # avoid reprocessing historical backlog on restart
                try:
                    msg_age = time.time() - float(msg_id)
                    if msg_age > MAX_MESSAGE_AGE:
                        continue
                except (ValueError, TypeError):
                    pass

                if check_for_mention(msg, agent):
                    user = msg.get("user", "") or msg.get("username", "Unknown")
                    is_audio = has_audio_attachment(msg)
                    msg_type = "audio_message" if is_audio else "mention"
                    
                    # Build message text — include audio file info if present
                    msg_text = msg.get("text", "")
                    audio_files = []
                    if is_audio:
                        for f in msg.get("files", []):
                            mimetype = f.get("mimetype", "")
                            subtype = f.get("subtype", "")
                            if mimetype.startswith("audio/") or subtype == "voice_message":
                                audio_files.append({
                                    "name": f.get("name", "audio"),
                                    "mimetype": mimetype,
                                    "url": f.get("url_private_download", ""),
                                })
                        print(f"  🎤 New audio/voice message from {user}", flush=True)
                    else:
                        print(f"  📬 New mention from {user}: {msg_text[:50]}...", flush=True)
                    
                    pending_messages.append({
                        "user": user,
                        "text": msg_text,
                        "timestamp": msg_id,
                        "thread_ts": msg_id,  # Thread replies under the user's original message
                        "type": msg_type,
                        "audio_files": audio_files,
                    })
            
            # Check for thread replies (reuse same raw_messages — no second API call)
            if rate_limiter.consecutive_rate_limits == 0:
                # Get list of agent's own thread timestamps
                agent_thread_timestamps = set(m.get("ts") for m in agent_data.get("messages", []) if m.get("ts"))
                
                threads_checked = 0
                for raw_msg in raw_messages:
                    if threads_checked >= 2:  # Limit threads per cycle (reduced from 3 to save API calls)
                        break
                    
                    reply_count = raw_msg.get("reply_count", 0)
                    if reply_count == 0:
                        continue
                    
                    thread_ts = raw_msg.get("ts")
                    latest_reply = raw_msg.get("latest_reply", "")
                    
                    # Check if this is agent's own thread
                    msg_user = raw_msg.get("user", "") or raw_msg.get("username", "")
                    is_agent_thread = (
                        agent["name"].lower() in msg_user.lower() or
                        thread_ts in agent_thread_timestamps
                    )
                    
                    # Check if we've seen this latest reply
                    reply_key = f"{thread_ts}:{latest_reply}"
                    if reply_key in agent_data.get("seen_replies", []):
                        continue
                    
                    # Get thread replies
                    if rate_limiter.is_backing_off():
                        break
                    
                    replies, was_rate_limited = get_thread_replies(thread_ts)
                    threads_checked += 1
                    
                    if was_rate_limited:
                        rate_limiter.on_rate_limit()
                        break
                    
                    # Check each reply
                    for reply in replies[1:]:  # Skip parent message
                        reply_ts = reply.get("ts", "") or reply.get("timestamp", "")
                        reply_id = f"{thread_ts}:{reply_ts}"
                        
                        if reply_id in agent_data.get("seen_replies", []):
                            continue
                        
                        # Skip agent's own messages
                        reply_user = reply.get("user", "") or reply.get("username", "")
                        if agent["name"].lower() in reply_user.lower():
                            agent_data.setdefault("seen_replies", []).append(reply_id)
                            continue
                        
                        # Check if should respond
                        reply_text = reply.get("text", "").lower()
                        is_mention = any(m.lower() in reply_text for m in agent["mentions"])
                        should_respond = is_agent_thread or is_mention
                        
                        if should_respond:
                            print(f"  🧵 New thread reply from {reply_user}: {reply.get('text', '')[:50]}...")
                            pending_messages.append({
                                "user": reply_user or "Unknown",
                                "text": reply.get("text", ""),
                                "timestamp": reply_ts,
                                "thread_ts": thread_ts,
                                "type": "thread_reply"
                            })
                        
                        # Mark as seen
                        agent_data.setdefault("seen_replies", []).append(reply_id)
                    
                    # Mark latest reply as seen
                    agent_data.setdefault("seen_replies", []).append(reply_key)
            
            # Process all pending messages in one batch
            if pending_messages:
                # Save seen_messages BEFORE spawning Claude — if process is killed
                # during the (long) Claude call, messages won't be re-processed on restart
                save_seen_messages(seen_messages)
                save_agent_messages(agent_data)
                print(f"\n📋 Processing {len(pending_messages)} pending message(s) in batch...", flush=True)
                run_batched_response(agent, pending_messages)

            # Save state (also saves after non-mention polls to track all seen messages)
            save_seen_messages(seen_messages)
            save_agent_messages(agent_data)
            
            # Wait for next poll
            jitter = random.uniform(0, POLL_JITTER)
            sleep_time = args.interval + jitter
            
            if rate_limiter.consecutive_rate_limits > 0:
                sleep_time += BACKOFF_INITIAL / 2
                print(f"💤 Extended sleep due to recent rate limits: {sleep_time:.0f}s", flush=True)
            
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped")
        save_seen_messages(seen_messages)
        save_agent_messages(agent_data)


if __name__ == "__main__":
    main()
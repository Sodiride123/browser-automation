#!/usr/bin/env python3
"""
Phantom CLI — Run browser automation tasks from the command line.

Usage:
    python phantom/run.py "Go to google.com and search for AI news"
    python phantom/run.py "Take a screenshot of example.com" --url example.com
    python phantom/run.py --preset screenshot --url https://example.com
    python phantom/run.py --preset search --query "AI news 2026"
    python phantom/run.py --preset extract --url https://example.com --headless
    python phantom/run.py --list-presets
"""

import argparse
import json
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phantom.agent import PhantomAgent
from phantom.config import PhantomConfig
from phantom.presets import get_preset_task, list_presets


def main():
    parser = argparse.ArgumentParser(
        description="Phantom — Browser Automation Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Go to google.com and search for AI news"
  %(prog)s "Take a screenshot of example.com" --url https://example.com
  %(prog)s "Extract the main heading" --url https://example.com --headless
  %(prog)s --preset screenshot --url https://example.com
  %(prog)s --preset search --query "AI news 2026"
  %(prog)s --preset extract --url https://example.com
  %(prog)s --list-presets
        """,
    )
    parser.add_argument("task", nargs="?", default=None, help="Natural language task description")
    parser.add_argument("--preset", "-p", help="Use a preset task (screenshot, extract, search, etc.)")
    parser.add_argument("--query", "-q", help="Query text for preset tasks (e.g., search query)")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")
    parser.add_argument("--url", "-u", help="Starting URL (optional)")
    parser.add_argument("--model", "-m", default=None, help="LLM model (default: claude-sonnet-4-6)")
    parser.add_argument("--max-steps", type=int, default=None, help="Max steps (default: 30)")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (no VNC)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print step-by-step output")
    parser.add_argument("--proxy", help="Proxy URL (e.g. http://proxy:8080)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--config", help="Path to config.json file")

    args = parser.parse_args()

    # Handle --list-presets
    if args.list_presets:
        print(list_presets())
        sys.exit(0)

    # Resolve task from preset or positional argument
    if args.preset:
        try:
            task = get_preset_task(args.preset, url=args.url, query=args.query)
        except ValueError as e:
            parser.error(str(e))
    elif args.task:
        task = args.task
    else:
        parser.error("Either a task description or --preset is required")

    # Build config
    config = PhantomConfig.load(args.config)
    if args.model:
        config.model = args.model
    if args.max_steps:
        config.max_steps = args.max_steps
    if args.headless:
        config.headless = True
    if args.verbose:
        config.verbose = True
    if args.proxy:
        config.proxy = args.proxy

    # Run agent
    agent = PhantomAgent(config=config)
    result = agent.run(task=task, url=args.url if not args.preset else None)

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status_emoji = {
            "done": "✅",
            "fail": "❌",
            "need_human": "🙋",
            "max_steps": "⏱️",
        }.get(result["status"], "❓")

        print(f"\n{status_emoji} Status: {result['status']}")
        print(f"📝 Result: {result['result']}")
        print(f"📊 Steps: {result['steps']}")

        if result["status"] == "need_human":
            print(f"🖥️  VNC: {result.get('vnc_hint', 'Connect to port 6080')}")

    # Exit code: 0 for done, 1 for failure
    sys.exit(0 if result["status"] == "done" else 1)


if __name__ == "__main__":
    main()

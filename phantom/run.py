#!/usr/bin/env python3
"""
Phantom CLI — Run browser automation tasks from the command line.

Usage:
    python phantom/run.py "Go to google.com and search for AI news"
    python phantom/run.py "Take a screenshot of example.com" --url example.com
    python phantom/run.py "Fill out the contact form" --url example.com/contact --verbose
    python phantom/run.py "Extract all product prices" --url shop.example.com --headless
"""

import argparse
import json
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phantom.agent import PhantomAgent
from phantom.config import PhantomConfig


def main():
    parser = argparse.ArgumentParser(
        description="Phantom — Browser Automation Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Go to google.com and search for AI news"
  %(prog)s "Take a screenshot of example.com" --url https://example.com
  %(prog)s "Extract the main heading" --url https://example.com --headless
  %(prog)s "Fill the search box with 'hello'" --url https://google.com --verbose
        """,
    )
    parser.add_argument("task", help="Natural language task description")
    parser.add_argument("--url", "-u", help="Starting URL (optional)")
    parser.add_argument("--model", "-m", default=None, help="LLM model (default: claude-sonnet)")
    parser.add_argument("--max-steps", type=int, default=None, help="Max steps (default: 30)")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (no VNC)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print step-by-step output")
    parser.add_argument("--proxy", help="Proxy URL (e.g. http://proxy:8080)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--config", help="Path to config.json file")

    args = parser.parse_args()

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
    result = agent.run(task=args.task, url=args.url)

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

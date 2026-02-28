"""
Phantom — Browser Automation Agent

Usage:
    # CLI
    python -m phantom "Go to google.com and search for AI news"
    python phantom/run.py --preset screenshot --url https://example.com
    python phantom/run.py --list-presets

    # Python API
    from phantom import PhantomAgent
    agent = PhantomAgent()
    result = agent.run("Take a screenshot of example.com")

    # Presets
    from phantom.presets import get_preset_task
    task = get_preset_task("screenshot", url="https://example.com")
"""

from phantom.agent import PhantomAgent
from phantom.config import PhantomConfig
from phantom.presets import get_preset_task, list_presets

__all__ = ["PhantomAgent", "PhantomConfig", "get_preset_task", "list_presets"]

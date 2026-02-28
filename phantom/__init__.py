"""
Phantom — Browser Automation Agent

Usage:
    # CLI
    python -m phantom "Go to google.com and search for AI news"

    # Python API
    from phantom.agent import PhantomAgent
    agent = PhantomAgent()
    result = agent.run("Take a screenshot of example.com")
"""

from phantom.agent import PhantomAgent

__all__ = ["PhantomAgent"]

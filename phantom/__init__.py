"""
Phantom — Browser Automation Agent

Usage:
    # Via orchestrator (primary entry point)
    python -m phantom                              # Default work loop
    python -m phantom "Go to google.com and search for AI news"

    # Python API (for direct use in scripts)
    from phantom.observer import observe
    from phantom.actions import execute_action, set_elements
    from browser_interface import BrowserInterface

    browser = BrowserInterface()
    browser.start()
    obs = observe(browser, step=0)
    set_elements(obs["interactive_elements"])
    result = execute_action(browser, "click", {"selector": "#submit"})

    # Presets
    from phantom.presets import get_preset_task
    task = get_preset_task("screenshot", url="https://example.com")
"""

from phantom.config import PhantomConfig
from phantom.presets import get_preset_task, list_presets

__all__ = ["PhantomConfig", "get_preset_task", "list_presets"]
"""
Phantom Agent — The core observe-think-act loop.

Usage:
    from phantom.agent import PhantomAgent

    agent = PhantomAgent()
    result = agent.run("Go to google.com and search for AI news")
    print(result)
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

from browser_interface import BrowserInterface
from phantom.config import PhantomConfig, SCREENSHOTS_DIR
from phantom.observer import observe
from phantom.planner import plan_next_action
from phantom.actions import execute_action


class PhantomAgent:
    """
    Browser automation agent using an observe-think-act loop.

    The agent:
    1. Observes the page (screenshot + DOM extraction)
    2. Thinks (sends observation to LLM, gets next action)
    3. Acts (executes the action in the browser)
    4. Repeats until task is done, fails, or max steps reached
    """

    def __init__(self, config: Optional[PhantomConfig] = None):
        self.config = config or PhantomConfig.load()
        self.browser: Optional[BrowserInterface] = None
        self.history: list[dict] = []
        self._owns_browser = False

    def run(
        self,
        task: str,
        url: Optional[str] = None,
        browser: Optional[BrowserInterface] = None,
    ) -> dict:
        """
        Execute a browser automation task.

        Args:
            task: Natural language description of what to do
            url: Optional starting URL (navigates before the loop)
            browser: Optional existing BrowserInterface (agent won't close it)

        Returns:
            {
                "status": "done" | "fail" | "need_human" | "max_steps",
                "result": str,
                "steps": int,
                "history": list[dict],
            }
        """
        self.history = []

        # Setup browser
        if browser:
            self.browser = browser
            self._owns_browser = False
        else:
            self.browser = self._create_browser()
            self._owns_browser = True

        try:
            # Navigate to starting URL if provided
            if url:
                norm_url = url if url.startswith(("http://", "https://")) else "https://" + url
                self.browser.goto(norm_url, wait_until="load")
                if self.config.verbose:
                    print(f"[phantom] Navigated to {norm_url}")

            # Main observe-think-act loop
            for step in range(self.config.max_steps):
                if self.config.verbose:
                    print(f"\n[phantom] === Step {step + 1}/{self.config.max_steps} ===")

                # 1. Observe
                observation = observe(
                    self.browser,
                    step=step,
                    screenshot=self.config.screenshot_on_step,
                )
                if self.config.verbose:
                    print(f"[phantom] URL: {observation['url']}")
                    print(f"[phantom] Title: {observation['title']}")

                # 2. Think (plan next action)
                plan = plan_next_action(observation, task, self.history, self.config)
                if self.config.verbose:
                    print(f"[phantom] Thought: {plan['thought']}")
                    print(f"[phantom] Action: {plan['action']}({json.dumps(plan['params'])})")

                # 3. Act
                action_name = plan["action"]
                action_params = plan["params"]
                result = execute_action(self.browser, action_name, action_params)
                if self.config.verbose:
                    print(f"[phantom] Result: {result}")

                # Record in history
                self.history.append({
                    "step": step + 1,
                    "thought": plan["thought"],
                    "action": action_name,
                    "params": action_params,
                    "result": result,
                })

                # Check terminal actions
                if action_name == "done":
                    return {
                        "status": "done",
                        "result": action_params.get("result", result),
                        "steps": step + 1,
                        "history": self.history,
                    }
                elif action_name == "fail":
                    return {
                        "status": "fail",
                        "result": action_params.get("reason", result),
                        "steps": step + 1,
                        "history": self.history,
                    }
                elif action_name == "need_human":
                    return {
                        "status": "need_human",
                        "result": action_params.get("reason", result),
                        "steps": step + 1,
                        "history": self.history,
                        "vnc_hint": "Connect to VNC at port 6080 to interact with the browser",
                    }

                # Check for action errors — if same error 3 times, bail
                if result.startswith("ERROR:"):
                    error_count = sum(
                        1 for h in self.history[-3:]
                        if h.get("result", "").startswith("ERROR:")
                    )
                    if error_count >= 3:
                        return {
                            "status": "fail",
                            "result": f"Repeated errors: {result}",
                            "steps": step + 1,
                            "history": self.history,
                        }

            # Max steps reached
            return {
                "status": "max_steps",
                "result": f"Reached max steps ({self.config.max_steps}) without completing task",
                "steps": self.config.max_steps,
                "history": self.history,
            }

        finally:
            if self._owns_browser and self.browser:
                self.browser.stop()
                self.browser = None

    def _create_browser(self) -> BrowserInterface:
        """Create a new BrowserInterface with config settings."""
        b = BrowserInterface(
            headless=self.config.headless,
            viewport_width=self.config.viewport_width,
            viewport_height=self.config.viewport_height,
            timeout=self.config.timeout,
            slow_mo=self.config.slow_mo,
        )
        b.start()
        return b

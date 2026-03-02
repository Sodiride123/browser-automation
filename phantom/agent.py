"""
Phantom Agent — The core observe-think-act loop.

Features:
- Accessibility tree for compact page representation
- Self-healing selectors with multi-strategy fallback
- Overlay auto-dismissal (cookie banners, popups)
- Loop detection to prevent infinite repetition
- VNC integration for human override

Usage:
    from phantom.agent import PhantomAgent

    agent = PhantomAgent()
    result = agent.run("Go to google.com and search for AI news")
    print(result)
"""

import json
import time
from typing import Optional

from browser_interface import BrowserInterface
from phantom.config import PhantomConfig, SCREENSHOTS_DIR
from phantom.observer import observe
from phantom.planner import plan_next_action
from phantom.actions import execute_action, set_elements, clear_selector_cache


class PhantomAgent:
    """
    Browser automation agent using an observe-think-act loop.

    The agent:
    1. Observes the page (accessibility tree + screenshot + interactive elements)
    2. Thinks (sends observation to LLM, gets next action)
    3. Acts (executes the action with self-healing selectors)
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
                    if observation.get("has_overlay"):
                        print("[phantom] ⚠️ Overlay detected")

                # Pass interactive elements to actions module for self-healing
                set_elements(observation.get("interactive_elements", []))

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
                    result_preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"[phantom] Result: {result_preview}")

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

                # Check for repeated errors with recovery attempts
                if result.startswith("ERROR:"):
                    error_count = sum(
                        1 for h in self.history[-3:]
                        if h.get("result", "").startswith("ERROR:")
                    )
                    if error_count == 2:
                        # Try recovery before giving up: clear cache + wait for page stability
                        self._attempt_recovery()
                    elif error_count >= 3:
                        return {
                            "status": "fail",
                            "result": f"Repeated errors: {result}",
                            "steps": step + 1,
                            "history": self.history,
                        }

                # Loop detection: same action+params repeated 3+ times
                if self._detect_loop():
                    if self.config.verbose:
                        print("[phantom] ⚠️ Loop detected — agent is repeating the same action")
                    return {
                        "status": "fail",
                        "result": "Loop detected: agent repeated the same action 3 times without progress",
                        "steps": step + 1,
                        "history": self.history,
                    }

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
            user_data_dir=self.config.user_data_dir,
            proxy=self.config.proxy,
        )
        b.start()
        return b

    def _attempt_recovery(self):
        """Try to recover from errors: clear caches, wait for page stability, dismiss overlays."""
        if self.config.verbose:
            print("[phantom] Attempting error recovery...")
        try:
            clear_selector_cache()
            # Wait for any pending navigation/loads to settle
            self.browser.page.wait_for_load_state("domcontentloaded", timeout=5000)
            time.sleep(0.5)
            # Try dismissing any overlay that might be blocking
            from phantom.actions import _dismiss_overlay
            _dismiss_overlay(self.browser)
        except Exception:
            pass  # Recovery is best-effort

    def _detect_loop(self) -> bool:
        """
        Detect if the agent is stuck in a loop.

        Checks three patterns:
        1. Exact repeat: same action + same params 3 times in a row
        2. Stagnation: same action type 4+ times in a row (even with different params)
           This catches cases where the agent keeps extracting HTML with slightly
           different selectors but never makes progress.
        3. Navigation loop: goto actions in last 6 steps with only 2 unique URLs
           (agent bouncing between two pages without making progress)
        """
        if len(self.history) < 3:
            return False

        # Pattern 1: Exact repeat (3 identical)
        last_3 = self.history[-3:]
        actions = [(h["action"], json.dumps(h["params"], sort_keys=True)) for h in last_3]
        if len(set(actions)) == 1:
            return True

        # Pattern 2: Stagnation (same action type 4+ times, excluding navigation/terminal)
        if len(self.history) >= 4:
            last_4 = self.history[-4:]
            action_names = [h["action"] for h in last_4]
            non_progress_actions = {"extract_text", "extract_html", "extract_attribute", "scroll_down", "scroll_up", "screenshot", "wait"}
            if len(set(action_names)) == 1 and action_names[0] in non_progress_actions:
                return True

        # Pattern 3: Navigation loop (bouncing between ≤2 URLs in last 6 steps)
        if len(self.history) >= 6:
            last_6 = self.history[-6:]
            goto_urls = [
                h["params"].get("url", "") for h in last_6
                if h["action"] == "goto"
            ]
            if len(goto_urls) >= 4 and len(set(goto_urls)) <= 2:
                return True

        return False

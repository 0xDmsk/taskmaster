import json
import os
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # Available only inside the playwright container


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int = 0) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


class BaseBrowserSkill(ABC):
    """
    Base class for browser-automation skills powered by Playwright.

    Mirrors BaseSkill's interface but replaces shell execution with a
    managed Playwright browser context.

    Subclasses must implement:
        run_browser(page, context, **kwargs) -> dict

    The orchestrator handles browser lifecycle, timing, loot saving,
    and JSON envelope assembly automatically.

    Optional class attributes:
        browser_type: str   — "chromium" (default), "firefox", or "webkit"
        headless: bool      — True (default)
        schema: dict | None — JSON Schema for the findings field
    """

    tool = "playwright"
    browser_type: str = "chromium"
    headless: bool = True
    schema: dict | None = None

    def __init__(self, target=None):
        self.target = target
        self.loot_path = "/loot"
        self._artifacts: list[str] = []
        self._errors: list[str] = []

    @abstractmethod
    def run_browser(self, page, context, **kwargs) -> dict:
        """
        Execute browser automation against self.target.

        Args:
            page:    Playwright Page object (fresh, no navigation yet)
            context: Playwright BrowserContext (use for multi-page flows)
            **kwargs: arguments from the task payload

        Returns:
            dict of findings (arbitrary structure, kept under findings key)
        """

    def run(self, **kwargs) -> dict:
        """
        Orchestrator: creates browser, calls run_browser(), closes browser,
        returns a JSON envelope compatible with the Taskmaster result format.
        """
        target = kwargs.pop("target", None) or self.target
        self.target = target
        self._artifacts = []
        self._errors = []

        started_at = datetime.now(timezone.utc).isoformat()
        skill_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        if skill_name.startswith("skills."):
            skill_name = skill_name[len("skills."):]

        findings = {}
        status = "success"

        try:
            if sync_playwright is None:
                raise RuntimeError(
                    "playwright is not installed. Run inside the playwright-operator container."
                )
            with sync_playwright() as pw:  # type: ignore[operator]
                launcher = getattr(pw, self.browser_type)
                browser = launcher.launch(**self._launch_options())
                context = browser.new_context(
                    ignore_https_errors=True,
                    **self._context_options(),
                )
                page = context.new_page()
                findings = self.run_browser(page, context, **kwargs)
                browser.close()
        except Exception:
            self._errors.append(traceback.format_exc())
            status = "error"

        completed_at = datetime.now(timezone.utc).isoformat()

        return {
            "skill": skill_name,
            "target": target,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "tool": self.tool,
            "tool_version": self._playwright_version(),
            "command": "",
            "findings": findings,
            "artifacts": list(self._artifacts),
            "errors": list(self._errors),
        }

    # ------------------------------------------------------------------ #
    # Helpers available to subclasses                                       #
    # ------------------------------------------------------------------ #

    def save_screenshot(self, page, filename: str) -> str:
        """Take a full-page screenshot and save to /loot."""
        path = os.path.join(self.loot_path, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        page.screenshot(path=path, full_page=True)
        self._artifacts.append(path)
        return path

    def save_artifact(self, filename: str, content: str) -> str:
        """Save text content to /loot and track as artifact."""
        path = os.path.join(self.loot_path, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        self._artifacts.append(path)
        return path

    def save_json(self, filename: str, data: dict) -> str:
        """Save a dict as JSON to /loot and track as artifact."""
        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(self.loot_path, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._artifacts.append(path)
        return path

    # ------------------------------------------------------------------ #
    # Internal                                                              #
    # ------------------------------------------------------------------ #

    def _context_options(self) -> dict:
        """
        Build extra options for browser.new_context().
        Automatically picks up BROWSER_PROXY env var (e.g. for Burp/ZAP).
        Override to add headers, viewport, storage state, etc.
        """
        options = {}
        proxy_url = os.environ.get("BROWSER_PROXY")
        if proxy_url:
            options["proxy"] = {"server": proxy_url}
        return options

    def _launch_options(self) -> dict:
        headless = _env_flag("PLAYWRIGHT_HEADLESS", self.headless)
        options = {"headless": headless}
        if self.browser_type == "chromium" and _env_flag("PLAYWRIGHT_DEVTOOLS"):
            options["args"] = ["--auto-open-devtools-for-tabs"]
        slow_mo = _env_int("PLAYWRIGHT_SLOW_MO_MS")
        if slow_mo > 0:
            options["slow_mo"] = slow_mo
        return options

    def _playwright_version(self) -> str:
        try:
            import playwright  # noqa: PLC0415
            return getattr(playwright, "__version__", "")
        except Exception:
            return ""


class RenderedPageObserve(BaseBrowserSkill):
    """
    Observe a rendered page using a resilient navigation strategy.

    Defaults to `domcontentloaded` plus a short settle delay instead of
    `networkidle`, which is often too brittle for apps with long-lived
    background requests or anti-bot challenges.
    """

    def run_browser(self, page, context, **kwargs) -> dict:
        target = kwargs.get("target") or self.target
        if not target:
            raise ValueError("target is required")

        wait_until = kwargs.get("wait_until", "domcontentloaded")
        timeout_ms = int(kwargs.get("timeout_ms", 90000))
        settle_ms = int(kwargs.get("settle_ms", 5000))
        text_limit = int(kwargs.get("text_limit", 2000))
        resource_limit = int(kwargs.get("resource_limit", 40))
        interactive_hold_ms = int(
            kwargs.get(
                "interactive_hold_ms",
                _env_int(
                    "PLAYWRIGHT_INTERACTIVE_HOLD_MS",
                    120000 if _env_flag("PLAYWRIGHT_INTERACTIVE") else 0,
                ),
            )
        )

        resources = []

        def on_response(resp):
            try:
                resources.append(
                    {
                        "url": resp.url,
                        "status": resp.status,
                        "content_type": (resp.headers or {}).get("content-type"),
                    }
                )
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(target, wait_until=wait_until, timeout=timeout_ms)
        if settle_ms > 0:
            page.wait_for_timeout(settle_ms)
        if interactive_hold_ms > 0:
            page.wait_for_timeout(interactive_hold_ms)

        body = page.locator("body")
        body_text = body.inner_text(timeout=15000)

        findings = {
            "final_url": page.url,
            "title": page.title(),
            "dom_counts": {
                "anchors": page.locator("a").count(),
                "scripts": page.locator("script").count(),
                "forms": page.locator("form").count(),
                "buttons": page.locator("button").count(),
            },
            "headings": page.locator("h1, h2, h3").all_inner_texts()[:10],
            "visible_text_sample": body_text[:text_limit],
            "resource_sample": resources[:resource_limit],
            "navigation_strategy": {
                "wait_until": wait_until,
                "timeout_ms": timeout_ms,
                "settle_ms": settle_ms,
            },
        }
        session_url = os.environ.get("PLAYWRIGHT_SESSION_URL")
        if session_url or interactive_hold_ms > 0:
            findings["interactive_session"] = {
                "enabled": True,
                "url": session_url,
                "hold_ms": interactive_hold_ms,
            }
        return findings

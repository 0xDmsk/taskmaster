"""
Unit tests for BaseBrowserSkill envelope assembly and helpers.

Playwright is not installed in the dev environment — the sync_playwright
context manager is mocked throughout so tests run without a browser.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from skills.browser import BaseBrowserSkill, RenderedPageObserve


# ------------------------------------------------------------------ #
# Concrete test subclasses                                             #
# ------------------------------------------------------------------ #


class TitleFetcher(BaseBrowserSkill):
    """Returns a fake page title as findings."""

    def run_browser(self, page, context, **kwargs) -> dict:
        return {"title": page.title()}


class ErrorSkill(BaseBrowserSkill):
    """Always raises inside run_browser."""

    def run_browser(self, page, context, **kwargs) -> dict:
        raise RuntimeError("browser exploded")


class ArtifactSkill(BaseBrowserSkill):
    """Saves a screenshot and a JSON artifact."""

    def run_browser(self, page, context, **kwargs) -> dict:
        self.save_screenshot(page, "shot.png")
        self.save_json("data.json", {"key": "value"})
        return {"saved": True}


class ResponseEventPage:
    def __init__(self):
        self._handlers = {}
        self._locators = {}
        self.url = "https://example.com/final"
        self._waits = []

    def on(self, event, handler):
        self._handlers[event] = handler

    def goto(self, target, wait_until=None, timeout=None):
        self._goto = {
            "target": target,
            "wait_until": wait_until,
            "timeout": timeout,
        }
        response = MagicMock()
        response.url = "https://example.com/api"
        response.status = 200
        response.headers = {"content-type": "application/json"}
        if "response" in self._handlers:
            self._handlers["response"](response)

    def wait_for_timeout(self, ms):
        self._waits.append(ms)

    def title(self):
        return "Rendered Example"

    def locator(self, selector):
        return self._locators[selector]


class LocatorMock:
    def __init__(self, count_value=0, inner_text_value="", all_texts=None):
        self._count_value = count_value
        self._inner_text_value = inner_text_value
        self._all_texts = all_texts or []

    def count(self):
        return self._count_value

    def inner_text(self, timeout=None):
        return self._inner_text_value

    def all_inner_texts(self):
        return self._all_texts


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _make_playwright_mock(page_title="Test Page"):
    """
    Build a mock chain for sync_playwright().

    Usage in tests:
        mock_ctx, mock_pw, mock_browser, mock_page = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            ...

    The code does: `with sync_playwright() as pw`
      sync_playwright() → mock_ctx
      mock_ctx.__enter__() → mock_pw
      mock_pw.chromium.launch() → mock_browser
      mock_browser.new_context() → mock_context
      mock_context.new_page() → mock_page
    """
    mock_page = MagicMock()
    mock_page.title.return_value = page_title

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.firefox.launch.return_value = mock_browser
    mock_pw.webkit.launch.return_value = mock_browser

    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_pw)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    return mock_ctx, mock_pw, mock_browser, mock_page


# ------------------------------------------------------------------ #
# Envelope assembly                                                    #
# ------------------------------------------------------------------ #


class TestEnvelopeAssembly:
    def test_success_envelope_structure(self):
        mock_ctx, _, _, _ = _make_playwright_mock("My SPA")
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            skill = TitleFetcher(target="https://example.com")
            result = skill.run()

        assert result["skill"].endswith("TitleFetcher")
        assert result["target"] == "https://example.com"
        assert result["status"] == "success"
        assert result["tool"] == "playwright"
        assert result["command"] == ""
        assert result["findings"] == {"title": "My SPA"}
        assert isinstance(result["artifacts"], list)
        assert isinstance(result["errors"], list)
        assert "started_at" in result
        assert "completed_at" in result

    def test_target_override_via_kwargs(self):
        mock_ctx, _, _, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            skill = TitleFetcher(target="original")
            result = skill.run(target="override")

        assert result["target"] == "override"

    def test_run_browser_receives_correct_page(self):
        mock_ctx, _, _, mock_page = _make_playwright_mock()

        received = {}

        class CaptureArgs(BaseBrowserSkill):
            def run_browser(self, page, context, **kwargs):
                received["page"] = page
                return {}

        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            CaptureArgs(target="t").run()

        assert received["page"] is mock_page


# ------------------------------------------------------------------ #
# Error handling                                                       #
# ------------------------------------------------------------------ #


class TestErrorHandling:
    def test_run_browser_exception_sets_error_status(self):
        mock_ctx, _, _, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            skill = ErrorSkill(target="https://example.com")
            result = skill.run()

        assert result["status"] == "error"
        assert result["findings"] == {}
        assert any("RuntimeError" in e or "browser exploded" in e for e in result["errors"])

    def test_error_envelope_has_all_keys(self):
        mock_ctx, _, _, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            result = ErrorSkill(target="t").run()

        for key in ("skill", "target", "status", "tool", "findings", "artifacts", "errors"):
            assert key in result

    def test_artifacts_cleared_between_runs(self):
        mock_ctx, _, _, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            skill = TitleFetcher(target="t")
            skill._artifacts = ["stale_artifact.png"]
            result = skill.run()

        assert result["artifacts"] == []

    def test_playwright_not_installed_raises_runtime_error(self):
        """If playwright is None (not installed), run() returns error envelope."""
        with patch("skills.browser.sync_playwright", None):
            result = TitleFetcher(target="t").run()

        assert result["status"] == "error"
        assert any("playwright is not installed" in e for e in result["errors"])


# ------------------------------------------------------------------ #
# Browser context options                                              #
# ------------------------------------------------------------------ #


class TestContextOptions:
    def test_no_proxy_by_default(self):
        mock_ctx, _, mock_browser, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            os.environ.pop("BROWSER_PROXY", None)
            TitleFetcher(target="t").run()

        call_kwargs = mock_browser.new_context.call_args.kwargs
        assert "proxy" not in call_kwargs

    def test_proxy_picked_up_from_env(self):
        mock_ctx, _, mock_browser, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            with patch.dict(os.environ, {"BROWSER_PROXY": "http://burp:8080"}):
                TitleFetcher(target="t").run()

        call_kwargs = mock_browser.new_context.call_args.kwargs
        assert call_kwargs["proxy"] == {"server": "http://burp:8080"}

    def test_ignore_https_errors_always_set(self):
        mock_ctx, _, mock_browser, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            TitleFetcher(target="t").run()

        call_kwargs = mock_browser.new_context.call_args.kwargs
        assert call_kwargs["ignore_https_errors"] is True

    def test_headless_true_by_default(self):
        mock_ctx, mock_pw, _, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            TitleFetcher(target="t").run()

        launch_kwargs = mock_pw.chromium.launch.call_args.kwargs
        assert launch_kwargs.get("headless") is True

    def test_env_can_force_headful_devtools_launch(self):
        mock_ctx, mock_pw, _, _ = _make_playwright_mock()
        with (
            patch("skills.browser.sync_playwright", return_value=mock_ctx),
            patch.dict(
                os.environ,
                {
                    "PLAYWRIGHT_HEADLESS": "false",
                    "PLAYWRIGHT_DEVTOOLS": "true",
                },
                clear=False,
            ),
        ):
            TitleFetcher(target="t").run()

        launch_kwargs = mock_pw.chromium.launch.call_args.kwargs
        assert launch_kwargs["headless"] is False
        assert launch_kwargs["args"] == ["--auto-open-devtools-for-tabs"]

    def test_browser_type_attribute_default(self):
        assert TitleFetcher(target="t").browser_type == "chromium"


class TestRenderedPageObserve:
    def test_uses_domcontentloaded_and_collects_rendered_findings(self):
        page = ResponseEventPage()
        page._locators = {
            "body": LocatorMock(inner_text_value="Visible text"),
            "a": LocatorMock(count_value=3),
            "script": LocatorMock(count_value=5),
            "form": LocatorMock(count_value=0),
            "button": LocatorMock(count_value=1),
            "h1, h2, h3": LocatorMock(all_texts=["Heading 1", "Heading 2"]),
        }

        skill = RenderedPageObserve(target="https://example.com")
        findings = skill.run_browser(page, context=MagicMock())

        assert page._goto["wait_until"] == "domcontentloaded"
        assert page._waits == [5000]
        assert findings["title"] == "Rendered Example"
        assert findings["dom_counts"]["scripts"] == 5
        assert findings["resource_sample"][0]["url"] == "https://example.com/api"
        assert findings["navigation_strategy"]["wait_until"] == "domcontentloaded"

    def test_interactive_hold_and_session_url_are_exposed(self):
        page = ResponseEventPage()
        page._locators = {
            "body": LocatorMock(inner_text_value="Visible text"),
            "a": LocatorMock(count_value=1),
            "script": LocatorMock(count_value=2),
            "form": LocatorMock(count_value=0),
            "button": LocatorMock(count_value=0),
            "h1, h2, h3": LocatorMock(all_texts=["Heading 1"]),
        }

        with patch.dict(
            os.environ,
            {
                "PLAYWRIGHT_INTERACTIVE": "1",
                "PLAYWRIGHT_INTERACTIVE_HOLD_MS": "45000",
                "PLAYWRIGHT_SESSION_URL": "http://127.0.0.1:6081/vnc.html",
            },
            clear=False,
        ):
            findings = RenderedPageObserve(target="https://example.com").run_browser(
                page, context=MagicMock()
            )

        assert page._waits == [5000, 45000]
        assert findings["interactive_session"] == {
            "enabled": True,
            "url": "http://127.0.0.1:6081/vnc.html",
            "hold_ms": 45000,
        }


# ------------------------------------------------------------------ #
# Artifact helpers                                                     #
# ------------------------------------------------------------------ #


class TestArtifactHelpers:
    def test_save_screenshot_tracked(self, tmp_path):
        skill = ArtifactSkill(target="t")
        skill.loot_path = str(tmp_path)

        mock_ctx, _, _, mock_page = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            result = skill.run()

        screenshot_path = str(tmp_path / "shot.png")
        assert screenshot_path in result["artifacts"]
        mock_page.screenshot.assert_called_once_with(path=screenshot_path, full_page=True)

    def test_save_json_tracked(self, tmp_path):
        skill = ArtifactSkill(target="t")
        skill.loot_path = str(tmp_path)

        mock_ctx, _, _, _ = _make_playwright_mock()
        with patch("skills.browser.sync_playwright", return_value=mock_ctx):
            result = skill.run()

        json_path = str(tmp_path / "data.json")
        assert json_path in result["artifacts"]
        with open(json_path) as f:
            assert json.load(f) == {"key": "value"}

    def test_save_artifact_text(self, tmp_path):
        skill = TitleFetcher(target="t")
        skill.loot_path = str(tmp_path)
        path = skill.save_artifact("report.txt", "hello world")
        assert path in skill._artifacts
        with open(path) as f:
            assert f.read() == "hello world"

    def test_save_json_adds_extension(self, tmp_path):
        skill = TitleFetcher(target="t")
        skill.loot_path = str(tmp_path)
        path = skill.save_json("no_extension", {"x": 1})
        assert path.endswith(".json")


# ------------------------------------------------------------------ #
# Playwright version detection                                          #
# ------------------------------------------------------------------ #


class TestVersionDetection:
    def test_returns_version_string_when_available(self):
        mock_playwright_module = MagicMock()
        mock_playwright_module.__version__ = "1.48.0"
        with patch.dict(sys.modules, {"playwright": mock_playwright_module}):
            version = TitleFetcher(target="t")._playwright_version()
        assert version == "1.48.0"

    def test_returns_empty_string_on_import_error(self):
        with patch.dict(sys.modules, {"playwright": None}):
            version = TitleFetcher(target="t")._playwright_version()
        assert version == ""

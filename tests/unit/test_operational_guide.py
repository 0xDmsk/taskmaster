"""Tests for the operational-guide delivery channels."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools import get_operational_guide as gog


def test_load_guide_returns_full_document():
    text = gog.load_guide()
    assert "Core loop" in text
    assert "Reporting database workflow" in text
    assert "Threat modeling" in text


def test_core_instructions_is_the_marked_section_only():
    core = gog.core_instructions()
    assert "Core loop" in core
    assert "request_playbook" in core
    # The core is a concise subset — the detailed reporting section is excluded.
    assert "Reporting database workflow" not in core
    # Delimiter comments are stripped.
    assert "MCP-INSTRUCTIONS-START" not in core
    assert "MCP-INSTRUCTIONS-END" not in core


def test_core_instructions_is_meaningfully_shorter_than_full_guide():
    assert len(gog.core_instructions()) < len(gog.load_guide())


def test_handle_get_operational_guide_returns_guide():
    result = gog.handle_get_operational_guide({})
    assert "guide" in result
    assert "Core loop" in result["guide"]


def test_fallback_when_guide_missing(monkeypatch):
    monkeypatch.setattr(gog, "GUIDE_PATH", "/nonexistent/path/OPERATIONAL_GUIDE.md")
    assert gog.load_guide() == gog._FALLBACK
    # core_instructions falls back too (no markers in the fallback string).
    assert gog.core_instructions() == gog._FALLBACK

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dashboard import render_analysis


class TestDashboardMarkdownNormalization:
    """The dashboard preview shares normalize_report_markdown with the DOCX path, so
    the same •-shorthand / escaped-ordered markers render as real lists in the web UI."""

    def test_literal_bullets_render_as_unordered_list(self):
        html = str(render_analysis("Trace:\n• reads path\n• writes path"))
        assert "<ul" in html
        assert "<li>reads path</li>" in html
        assert "<li>writes path</li>" in html
        assert "•" not in html  # glyph was converted to a marker, not shown literally

    def test_escaped_ordered_markers_render_as_ordered_list(self):
        html = str(render_analysis("Steps:\n1\\. first\n2\\. second"))
        assert "<ol" in html
        assert "<li>first</li>" in html
        assert "<li>second</li>" in html

    def test_plain_prose_is_untouched(self):
        html = str(render_analysis("just a sentence, no list"))
        assert "<ul" not in html
        assert "<ol" not in html
        assert "just a sentence, no list" in html

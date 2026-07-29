#!/usr/bin/env python3
"""One-time import of pwndoc-ng vulnerability templates into Taskmaster.

Taskmaster keeps its own native ``finding_templates`` library (see
``state/reporting.py``); this script seeds it once from a pwndoc export. It is a
*content copy*, not a live sync — no pwndoc IDs are stored, and re-running it
de-duplicates by title rather than tracking pwndoc identity.

Input is the JSON returned by the pwndoc MCP ``list_vulnerabilities`` tool
(``{"status": "success", "datas": [...]}``). Fetch it once, save it to a file,
then run::

    uv run python scripts/import_pwndoc_templates.py --file pwndoc_vulns.json
    uv run python scripts/import_pwndoc_templates.py --file pwndoc_vulns.json --dry-run

pwndoc field -> template field:
    details[en].description  -> description
    details[en].observation  -> impact
    details[en].remediation  -> remediation
    details[en].references[] -> references (http(s) only)
    cvssv3                    -> cvss_vector
    category                 -> category (already mirrors the Taskmaster enum)
Severity has no pwndoc equivalent on a template, so it defaults to "Info" — you
set the real severity when instantiating the template into a finding.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from state import storage
from state.reporting import (
    create_finding_template,
    list_finding_templates,
    normalize_category,
)

_TITLE_PREFIX_RE = re.compile(r"^\s*BHI-OFFSEC-\S+\s+")
_BLANKS_RE = re.compile(r"\n{3,}")


class _HTMLToMarkdown(HTMLParser):
    """Small HTML -> Markdown converter for pwndoc rich-text fields.

    Handles paragraphs, line breaks, headings, bold/italic/code, links, ordered
    and unordered lists, and tables (as Markdown pipe tables). Unknown tags are
    dropped but their text is kept.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._list_stack: list[str] = []  # 'ul' | 'ol'
        self._ol_counter: list[int] = []
        # Table accumulation
        self._in_table = False
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._row_is_header = False
        self._header_rows: list[bool] = []
        self._li_fresh = False  # just opened an <li>; suppress its first <p> break

    # -- helpers ---------------------------------------------------------
    def _emit(self, text: str):
        if self._cell is not None:
            self._cell.append(text)
        else:
            self.out.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "div"):
            if self._in_table:
                pass
            elif self._list_stack:
                # A <p> wrapping list-item text must not break the bullet line.
                if not self._li_fresh:
                    self._emit(" ")
                self._li_fresh = False
            else:
                self._emit("\n\n")
        elif tag == "br":
            self._emit("\n")
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")
        elif tag == "code":
            self._emit("`")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._emit("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "a":
            self._link_href = dict(attrs).get("href", "")
            self._emit("[")
        elif tag == "ul":
            self._list_stack.append("ul")
            self._emit("\n")
        elif tag == "ol":
            self._list_stack.append("ol")
            self._ol_counter.append(0)
            self._emit("\n")
        elif tag == "li":
            indent = "  " * (len(self._list_stack) - 1)
            if self._list_stack and self._list_stack[-1] == "ol":
                self._ol_counter[-1] += 1
                self._emit(f"\n{indent}{self._ol_counter[-1]}. ")
            else:
                self._emit(f"\n{indent}- ")
            self._li_fresh = True
        elif tag == "table":
            self._in_table = True
            self._rows = []
            self._header_rows = []
        elif tag == "tr" and self._in_table:
            self._row = []
            self._row_is_header = False
        elif tag in ("td", "th") and self._in_table:
            self._cell = []
            if tag == "th":
                self._row_is_header = True

    def handle_endtag(self, tag):
        if tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")
        elif tag == "code":
            self._emit("`")
        elif tag == "a":
            href = getattr(self, "_link_href", "")
            self._emit(f"]({href})" if href else "]")
        elif tag in ("ul", "ol"):
            if self._list_stack:
                popped = self._list_stack.pop()
                if popped == "ol" and self._ol_counter:
                    self._ol_counter.pop()
            self._emit("\n")
        elif tag in ("td", "th") and self._in_table:
            text = "".join(self._cell or []).strip().replace("\n", " ")
            if self._row is not None:
                self._row.append(text)
            self._cell = None
        elif tag == "tr" and self._in_table:
            if self._row is not None:
                self._rows.append(self._row)
                self._header_rows.append(self._row_is_header)
            self._row = None
        elif tag == "table":
            self._in_table = False
            self._emit(self._render_table())
            self._rows = []
            self._header_rows = []

    def handle_data(self, data):
        if self._in_table and self._cell is None:
            return  # stray whitespace between table tags
        self._emit(data)

    def _render_table(self) -> str:
        rows = [r for r in self._rows if any(c.strip() for c in r)]
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        header = rows[0]
        body = rows[1:]
        lines = ["", "| " + " | ".join(header) + " |",
                 "| " + " | ".join(["---"] * width) + " |"]
        for r in body:
            lines.append("| " + " | ".join(r) + " |")
        lines.append("")
        return "\n".join(lines)

    def result(self) -> str:
        text = "".join(self.out)
        text = _BLANKS_RE.sub("\n\n", text)
        return text.strip()


def html_to_markdown(html: str) -> str:
    if not html:
        return ""
    parser = _HTMLToMarkdown()
    parser.feed(html)
    return parser.result()


def clean_title(raw: str) -> str:
    stripped = _TITLE_PREFIX_RE.sub("", raw or "").strip()
    return stripped or (raw or "").strip()


def map_vulnerability(vuln: dict) -> dict | None:
    """Map a pwndoc vulnerability record to a create_finding_template payload."""
    detail = next(
        (d for d in vuln.get("details", []) if d.get("locale") == "en"),
        None,
    )
    if not detail:
        return None
    title = clean_title(detail.get("title", ""))
    if not title:
        return None

    references = [
        ref.strip()
        for ref in (detail.get("references") or [])
        if isinstance(ref, str) and ref.strip().lower().startswith("http")
    ]

    return {
        "title": title,
        "severity": "Info",
        "category": normalize_category(vuln.get("category")),
        "description": html_to_markdown(detail.get("description", "")),
        "impact": html_to_markdown(detail.get("observation", "")),
        "proof_of_concept": "",
        "remediation": html_to_markdown(detail.get("remediation", "")),
        "cvss_vector": vuln.get("cvssv3") or None,
        "references": references,
        "source": "pwndoc",
        "created_by": "pwndoc-import",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True, help="pwndoc list_vulnerabilities JSON export")
    ap.add_argument("--dry-run", action="store_true", help="Parse and report, do not write")
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as fh:
        payload = json.load(fh)
    vulns = payload.get("datas", payload if isinstance(payload, list) else [])
    print(f"Loaded {len(vulns)} pwndoc vulnerabilities from {args.file}")

    storage._ensure_db()
    existing_titles = {t["title"].strip().lower() for t in list_finding_templates()}

    created = skipped_dup = skipped_empty = 0
    seen_this_run: set[str] = set()
    for vuln in vulns:
        payload = map_vulnerability(vuln)
        if not payload:
            skipped_empty += 1
            continue
        key = payload["title"].strip().lower()
        if key in existing_titles or key in seen_this_run:
            skipped_dup += 1
            continue
        seen_this_run.add(key)
        if args.dry_run:
            created += 1
            continue
        create_finding_template(**payload)
        created += 1

    verb = "Would create" if args.dry_run else "Created"
    print(f"{verb}: {created}   skipped (duplicate title): {skipped_dup}   "
          f"skipped (no en detail/title): {skipped_empty}")


if __name__ == "__main__":
    main()

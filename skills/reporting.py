"""
Reporting skills — render structured findings into branded deliverables.

These skills bypass the CLI-tool execution model that `BaseSkill` is
built around. Each subclass implements `render()` and the orchestrator
`run()` produces the standard Taskmaster JSON envelope so the dashboard
and audit log treat report tasks identically to other executions.

Layout contract for the docxtpl template (see
`scripts/build_finding_template.py` for how it is produced from a
source docx):

    finding.id              str    e.g. "BHI-OFFSEC-25.05.F01"
    finding.title           str
    finding.severity        str    Critical/High/Medium/Low/Info
    finding.category        str    Web/API/Cloud/Infra/etc
    finding.cvss.score      str    "8.6"
    finding.cvss.vector     str    "AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N"
    finding.affected        str    host / IP / endpoint
    finding.description     str
    finding.impact          str
    finding.proof_of_concept str
    finding.remediation     str
    finding.references      list[str]

Content contract (the rendered docx goes to the client — write for them,
not for the internal team):

  * **Plain language, no internal jargon.** Do not reference
    `Findings.md`, `recon-data.md`, `F-NNN` IDs, or `§N.M` section
    markers. Those files are working artifacts, not deliverables —
    citing them is confusing and leaks internal triage state. When you
    need to ground a claim, reference something the client can verify
    on their own: a URL, parameter, response header, or an artifact
    saved to `/loot`.

  * **One job per field.**
      - description       — *what* was found, in concrete terms (the
                            affected component, the behavior observed,
                            the class of issue). One or two sentences.
      - impact            — *why it matters* in business or technical
                            consequences a non-pentester can grasp.
                            Avoid vague "severe security impact"
                            phrasing; describe the specific harm.
      - proof_of_concept  — *how to reproduce*. A self-contained
                            request, payload, or command sequence that
                            a reader can follow without prior context.
                            Use Markdown fenced code blocks for raw
                            requests/payloads and single backticks for
                            inline parameters, headers, paths, and tokens;
                            the renderer converts those to monospace Word
                            runs after docxtpl renders the template.
      - remediation       — *what to do*. Specific, actionable steps
                            (e.g. "apply output encoding on the `q`
                            parameter and serve a CSP that disallows
                            inline scripts"), not generic platitudes
                            ("implement XSS defenses").

  * **Be succinct.** A few short paragraphs per field is plenty. The
    template's table layout breaks visual rhythm with wall-of-text
    prose.

  * **Severity is a final value**, not a working estimate. Strip any
    "(pending triage)" or similar qualifiers before rendering.
"""

from __future__ import annotations

import copy
import io
import json
import os
import re
import tempfile
import traceback
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from docxtpl import DocxTemplate
    from jinja2 import Environment as _JinjaEnvironment
except ImportError:  # Available inside the reporting container and dev venv
    DocxTemplate = None  # type: ignore[assignment]
    _JinjaEnvironment = None  # type: ignore[assignment]

try:
    from pygments import lex as _pygments_lex
    from pygments.lexers import get_lexer_by_name as _pygments_get_lexer_by_name
    from pygments.token import Comment as _PygmentsComment
    from pygments.token import Error as _PygmentsError
    from pygments.token import Generic as _PygmentsGeneric
    from pygments.token import Keyword as _PygmentsKeyword
    from pygments.token import Name as _PygmentsName
    from pygments.token import Number as _PygmentsNumber
    from pygments.token import Operator as _PygmentsOperator
    from pygments.token import String as _PygmentsString
    from pygments.util import ClassNotFound as _PygmentsClassNotFound
except ImportError:  # Syntax highlighting is best-effort.
    _pygments_lex = None
    _pygments_get_lexer_by_name = None
    _PygmentsClassNotFound = Exception  # type: ignore[assignment]
    _PygmentsComment = None
    _PygmentsError = None
    _PygmentsGeneric = None
    _PygmentsKeyword = None
    _PygmentsName = None
    _PygmentsNumber = None
    _PygmentsOperator = None
    _PygmentsString = None


# Default template lives at <project_root>/templates/finding_template.docx
# when running on the host, and at /app/templates/finding_template.docx
# inside the reporting container (matches Dockerfile.reporting COPY layout).
_DEFAULT_TEMPLATE_CANDIDATES = (
    "/app/templates/finding_template.docx",
    str(Path(__file__).resolve().parent.parent / "templates" / "finding_template.docx"),
)


def _default_template_path() -> str:
    for candidate in _DEFAULT_TEMPLATE_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return _DEFAULT_TEMPLATE_CANDIDATES[-1]


_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")
_FENCE_RE = re.compile(r"^\s*```\s*(?P<language>[A-Za-z0-9_+.-]*)\s*$")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML_NS = "http://www.w3.org/XML/1998/namespace"
_W = f"{{{_W_NS}}}"
_XML = f"{{{_XML_NS}}}"
_INLINE_CODE_COLOR = "188038"
_CODE_TEXT_COLOR = "24292F"
_CODE_BACKGROUND = "F6F8FA"
_CODE_BORDER = "D0D7DE"

ET.register_namespace("w", _W_NS)


def _slugify(text: str, fallback: str = "finding") -> str:
    slug = _SLUG_RE.sub("-", text or "").strip("-")
    return slug or fallback


_REQUIRED_FIELDS = (
    "id",
    "title",
    "severity",
    "category",
    "affected",
    "description",
    "impact",
    "proof_of_concept",
    "remediation",
)


def _normalize_finding(raw: dict) -> dict:
    """Coerce a finding dict into the shape the template expects.

    Accepts both flat (`cvss_score`, `cvss_vector`) and nested
    (`cvss: {score, vector}`) shapes so the agent isn't locked into one
    JSON layout.
    """
    if not isinstance(raw, dict):
        raise ValueError("finding must be a dict")

    missing = [field for field in _REQUIRED_FIELDS if not raw.get(field)]
    if missing:
        raise ValueError(f"finding missing required fields: {', '.join(missing)}")

    cvss = raw.get("cvss") or {}
    if not isinstance(cvss, dict):
        cvss = {}
    cvss_score = cvss.get("score") or raw.get("cvss_score") or ""
    cvss_vector = cvss.get("vector") or raw.get("cvss_vector") or ""

    references = raw.get("references") or []
    if isinstance(references, str):
        references = [line.strip() for line in references.splitlines() if line.strip()]

    return {
        "id": str(raw["id"]),
        "title": str(raw["title"]),
        "severity": str(raw["severity"]),
        "category": str(raw["category"]),
        "cvss": {"score": str(cvss_score), "vector": str(cvss_vector)},
        "affected": str(raw["affected"]),
        "description": str(raw["description"]),
        "impact": str(raw["impact"]),
        "proof_of_concept": str(raw["proof_of_concept"]),
        "remediation": str(raw["remediation"]),
        "references": [str(r) for r in references],
    }


def _contains_rich_markdown(text: str) -> bool:
    return "\n" in text or "```" in text or _INLINE_CODE_RE.search(text) is not None


def _split_markdown_blocks(text: str) -> list[tuple[str, str, str]]:
    """Split a small Markdown subset into plain and fenced-code blocks."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[tuple[str, str, str]] = []
    plain: list[str] = []
    code: list[str] = []
    code_language = ""
    in_code = False

    def flush_plain() -> None:
        nonlocal plain
        for line in plain:
            if line.strip():
                blocks.append(("plain", line, ""))
        plain = []

    def flush_code() -> None:
        nonlocal code, code_language
        blocks.append(("code", "\n".join(code), code_language))
        code = []
        code_language = ""

    for line in lines:
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_plain()
                code_language = fence_match.group("language").lower()
                in_code = True
            continue
        if in_code:
            code.append(line)
        else:
            plain.append(line)

    if in_code:
        flush_code()
    else:
        flush_plain()

    return blocks or [("plain", "", "")]


def _paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{_W}t":
            parts.append(node.text or "")
        elif node.tag == f"{_W}tab":
            parts.append("\t")
        elif node.tag == f"{_W}br":
            parts.append("\n")
    return "".join(parts)


def _first_run_properties(paragraph: ET.Element) -> ET.Element | None:
    for run in paragraph.findall(f"{_W}r"):
        rpr = run.find(f"{_W}rPr")
        if rpr is not None:
            return copy.deepcopy(rpr)
    ppr = paragraph.find(f"{_W}pPr")
    if ppr is None:
        return None
    ppr_rpr = ppr.find(f"{_W}rPr")
    return copy.deepcopy(ppr_rpr) if ppr_rpr is not None else None


def _paragraph_properties(paragraph: ET.Element) -> ET.Element | None:
    ppr = paragraph.find(f"{_W}pPr")
    return copy.deepcopy(ppr) if ppr is not None else None


def _remove_run_property(rpr: ET.Element, local_names: set[str]) -> None:
    for child in list(rpr):
        if child.tag.startswith(_W) and child.tag[len(_W) :] in local_names:
            rpr.remove(child)


def _set_text(run: ET.Element, text: str) -> None:
    t = ET.SubElement(run, f"{_W}t")
    t.set(f"{_XML}space", "preserve")
    t.text = text


def _set_code_run_properties(
    run: ET.Element,
    base_rpr: ET.Element | None = None,
    *,
    block: bool = False,
    color: str | None = None,
    italic: bool = False,
    bold: bool = False,
) -> None:
    rpr = copy.deepcopy(base_rpr) if base_rpr is not None else ET.Element(f"{_W}rPr")
    _remove_run_property(rpr, {"rFonts", "color", "sz", "szCs", "i", "iCs", "b", "bCs"})

    fonts = ET.SubElement(rpr, f"{_W}rFonts")
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(f"{_W}{attr}", "Roboto Mono")

    color_el = ET.SubElement(rpr, f"{_W}color")
    effective_color = color or (_CODE_TEXT_COLOR if block else _INLINE_CODE_COLOR)
    color_el.set(f"{_W}val", effective_color)

    if block:
        size = ET.SubElement(rpr, f"{_W}sz")
        size.set(f"{_W}val", "18")
        size_cs = ET.SubElement(rpr, f"{_W}szCs")
        size_cs.set(f"{_W}val", "18")

    if italic:
        ET.SubElement(rpr, f"{_W}i")
        ET.SubElement(rpr, f"{_W}iCs")

    if bold:
        ET.SubElement(rpr, f"{_W}b")
        ET.SubElement(rpr, f"{_W}bCs")

    run.append(rpr)


def _set_plain_run_properties(run: ET.Element, base_rpr: ET.Element | None) -> None:
    if base_rpr is not None:
        run.append(copy.deepcopy(base_rpr))


def _plain_paragraph(
    text: str,
    base_ppr: ET.Element | None,
    base_rpr: ET.Element | None,
) -> ET.Element:
    paragraph = ET.Element(f"{_W}p")
    if base_ppr is not None:
        paragraph.append(copy.deepcopy(base_ppr))

    last = 0
    for match in _INLINE_CODE_RE.finditer(text):
        if match.start() > last:
            run = ET.SubElement(paragraph, f"{_W}r")
            _set_plain_run_properties(run, base_rpr)
            _set_text(run, text[last : match.start()])
        run = ET.SubElement(paragraph, f"{_W}r")
        _set_code_run_properties(run, base_rpr, block=False)
        _set_text(run, match.group(1))
        last = match.end()

    if last < len(text) or not list(paragraph.findall(f"{_W}r")):
        run = ET.SubElement(paragraph, f"{_W}r")
        _set_plain_run_properties(run, base_rpr)
        _set_text(run, text[last:])

    return paragraph


def _token_style(ttype) -> dict[str, str | bool]:
    if _PygmentsComment is not None and ttype in _PygmentsComment:
        return {"color": "6A737D", "italic": True}
    if _PygmentsKeyword is not None and ttype in _PygmentsKeyword:
        return {"color": "CF222E", "bold": True}
    if _PygmentsOperator is not None and ttype in _PygmentsOperator:
        return {"color": "CF222E"}
    if _PygmentsString is not None and ttype in _PygmentsString:
        return {"color": "0A3069"}
    if _PygmentsNumber is not None and ttype in _PygmentsNumber:
        return {"color": "0550AE"}
    if _PygmentsName is not None and ttype in _PygmentsName.Function:
        return {"color": "8250DF"}
    if _PygmentsName is not None and ttype in _PygmentsName.Class:
        return {"color": "8250DF", "bold": True}
    if _PygmentsName is not None and ttype in _PygmentsName.Decorator:
        return {"color": "8250DF"}
    if _PygmentsName is not None and ttype in _PygmentsName.Builtin:
        return {"color": "0550AE"}
    if _PygmentsName is not None and ttype in _PygmentsName.Attribute:
        return {"color": "953800"}
    if _PygmentsName is not None and ttype in _PygmentsName.Variable:
        return {"color": "953800"}
    if _PygmentsGeneric is not None and ttype in _PygmentsGeneric:
        return {"color": "57606A"}
    if _PygmentsError is not None and ttype in _PygmentsError:
        return {"color": "B31D28"}
    return {"color": _CODE_TEXT_COLOR}


def _code_line_spans(text: str, language: str) -> list[list[tuple[str, dict[str, str | bool]]]]:
    if _pygments_lex is None or _pygments_get_lexer_by_name is None or not language:
        return [[(line or " ", {"color": _CODE_TEXT_COLOR})] for line in text.split("\n")]

    try:
        lexer = _pygments_get_lexer_by_name(language)
    except _PygmentsClassNotFound:
        return [[(line or " ", {"color": _CODE_TEXT_COLOR})] for line in text.split("\n")]

    lines: list[list[tuple[str, dict[str, str | bool]]]] = [[]]
    for ttype, value in _pygments_lex(text, lexer):
        if not value:
            continue
        parts = value.split("\n")
        for idx, part in enumerate(parts):
            if idx:
                lines.append([])
            if part:
                lines[-1].append((part, _token_style(ttype)))

    if text.endswith("\n") and lines and not lines[-1]:
        lines.pop()
    return lines or [[(" ", {"color": _CODE_TEXT_COLOR})]]


def _code_paragraph(spans: list[tuple[str, dict[str, str | bool]]]) -> ET.Element:
    paragraph = ET.Element(f"{_W}p")
    ppr = ET.SubElement(paragraph, f"{_W}pPr")
    spacing = ET.SubElement(ppr, f"{_W}spacing")
    spacing.set(f"{_W}after", "0")
    spacing.set(f"{_W}lineRule", "auto")

    ppr_rpr = ET.SubElement(ppr, f"{_W}rPr")
    ppr_fonts = ET.SubElement(ppr_rpr, f"{_W}rFonts")
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        ppr_fonts.set(f"{_W}{attr}", "Roboto Mono")
    ppr_color = ET.SubElement(ppr_rpr, f"{_W}color")
    ppr_color.set(f"{_W}val", _CODE_TEXT_COLOR)
    ppr_size = ET.SubElement(ppr_rpr, f"{_W}sz")
    ppr_size.set(f"{_W}val", "18")
    ppr_size_cs = ET.SubElement(ppr_rpr, f"{_W}szCs")
    ppr_size_cs.set(f"{_W}val", "18")

    for text, style in spans or [(" ", {"color": _CODE_TEXT_COLOR})]:
        run = ET.SubElement(paragraph, f"{_W}r")
        _set_code_run_properties(
            run,
            block=True,
            color=style.get("color") if isinstance(style.get("color"), str) else None,
            italic=bool(style.get("italic")),
            bold=bool(style.get("bold")),
        )
        _set_text(run, text)
    return paragraph


def _table_border(parent: ET.Element, name: str, color: str = _CODE_BORDER) -> None:
    border = ET.SubElement(parent, f"{_W}{name}")
    border.set(f"{_W}val", "single")
    border.set(f"{_W}sz", "6")
    border.set(f"{_W}space", "0")
    border.set(f"{_W}color", color)


def _table_cell_margin(parent: ET.Element, name: str, width: str) -> None:
    margin = ET.SubElement(parent, f"{_W}{name}")
    margin.set(f"{_W}w", width)
    margin.set(f"{_W}type", "dxa")


def _code_table(text: str, language: str) -> ET.Element:
    """Return a shaded one-cell table that behaves like a DOCX code block."""
    table = ET.Element(f"{_W}tbl")
    tbl_pr = ET.SubElement(table, f"{_W}tblPr")

    tbl_w = ET.SubElement(tbl_pr, f"{_W}tblW")
    tbl_w.set(f"{_W}w", "5000")
    tbl_w.set(f"{_W}type", "pct")

    borders = ET.SubElement(tbl_pr, f"{_W}tblBorders")
    for name in ("top", "left", "bottom", "right"):
        _table_border(borders, name)
    for name in ("insideH", "insideV"):
        border = ET.SubElement(borders, f"{_W}{name}")
        border.set(f"{_W}val", "nil")

    layout = ET.SubElement(tbl_pr, f"{_W}tblLayout")
    layout.set(f"{_W}type", "fixed")

    grid = ET.SubElement(table, f"{_W}tblGrid")
    grid_col = ET.SubElement(grid, f"{_W}gridCol")
    grid_col.set(f"{_W}w", "9025")

    row = ET.SubElement(table, f"{_W}tr")
    cell = ET.SubElement(row, f"{_W}tc")
    tc_pr = ET.SubElement(cell, f"{_W}tcPr")

    tc_w = ET.SubElement(tc_pr, f"{_W}tcW")
    tc_w.set(f"{_W}w", "5000")
    tc_w.set(f"{_W}type", "pct")

    shading = ET.SubElement(tc_pr, f"{_W}shd")
    shading.set(f"{_W}val", "clear")
    shading.set(f"{_W}color", "auto")
    shading.set(f"{_W}fill", _CODE_BACKGROUND)

    margins = ET.SubElement(tc_pr, f"{_W}tcMar")
    _table_cell_margin(margins, "top", "120")
    _table_cell_margin(margins, "left", "160")
    _table_cell_margin(margins, "bottom", "120")
    _table_cell_margin(margins, "right", "160")

    for spans in _code_line_spans(text, language):
        cell.append(_code_paragraph(spans))

    return table


def _markdown_paragraphs(paragraph: ET.Element, text: str) -> list[ET.Element]:
    base_ppr = _paragraph_properties(paragraph)
    base_rpr = _first_run_properties(paragraph)
    replacement: list[ET.Element] = []

    for kind, value, language in _split_markdown_blocks(text):
        if kind == "code":
            replacement.append(_code_table(value, language))
        else:
            replacement.append(_plain_paragraph(value, base_ppr, base_rpr))

    return replacement


def _rewrite_markdown_paragraphs(parent: ET.Element) -> bool:
    changed = False
    index = 0
    while index < len(parent):
        child = parent[index]
        if child.tag == f"{_W}p":
            text = _paragraph_text(child)
            if _contains_rich_markdown(text):
                replacement = _markdown_paragraphs(child, text)
                parent[index : index + 1] = replacement
                index += len(replacement)
                changed = True
                continue
        if _rewrite_markdown_paragraphs(child):
            changed = True
        index += 1
    return changed


def _rewrite_document_xml_markdown(xml_bytes: bytes) -> tuple[bytes, bool]:
    # Preserve namespace prefixes that already exist in the template as much
    # as ElementTree allows. Word accepts prefix changes, but stable prefixes
    # keep the generated XML readable when diagnosing render bugs.
    for _, namespace in ET.iterparse(io.BytesIO(xml_bytes), events=("start-ns",)):
        prefix, uri = namespace
        if prefix:
            ET.register_namespace(prefix, uri)

    root = ET.fromstring(xml_bytes)
    changed = _rewrite_markdown_paragraphs(root)
    if not changed:
        return xml_bytes, False
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), True


def _rewrite_docx_markdown(path: str) -> bool:
    """Apply the report Markdown subset to word/document.xml in-place."""
    output_dir = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(path)}.",
        suffix=".tmp",
        dir=output_dir,
    )
    os.close(fd)

    changed = False
    try:
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(tmp_path, "w") as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "word/document.xml":
                    data, changed = _rewrite_document_xml_markdown(data)
                target.writestr(item, data)

        if changed:
            os.replace(tmp_path, path)
        else:
            os.unlink(tmp_path)
        return changed
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class BaseReportSkill(ABC):
    """Base class for non-shell skills that emit document artifacts.

    Mirrors `BaseSkill` / `BaseBrowserSkill` so the executor dispatcher
    and dashboard can treat report tasks as ordinary executions.
    """

    tool = "docxtpl"
    schema: dict | None = None

    def __init__(self, target: str | None = None):
        self.target = target
        self.loot_path = "/loot"
        self._artifacts: list[str] = []
        self._errors: list[str] = []

    @abstractmethod
    def render(self, **kwargs) -> dict:
        """Produce one or more artifacts and return a findings dict.

        Implementations should call `self.save_artifact_path()` for files
        they write directly to disk (the path is tracked automatically).
        """

    def run(self, **kwargs) -> dict:
        target = kwargs.pop("target", None) or self.target
        self.target = target
        self._artifacts = []
        self._errors = []

        started_at = datetime.now(timezone.utc).isoformat()
        skill_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        if skill_name.startswith("skills."):
            skill_name = skill_name[len("skills.") :]

        findings: dict = {}
        status = "success"
        try:
            findings = self.render(**kwargs) or {}
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
            "tool_version": self._docxtpl_version(),
            "command": "",
            "findings": findings,
            "artifacts": list(self._artifacts),
            "errors": list(self._errors),
        }

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def save_artifact_path(self, path: str) -> str:
        """Track an already-written file as an artifact."""
        self._artifacts.append(path)
        return path

    def save_json(self, filename: str, data: dict) -> str:
        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(self.loot_path, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._artifacts.append(path)
        return path

    def _docxtpl_version(self) -> str:
        try:
            import docxtpl  # noqa: PLC0415

            return getattr(docxtpl, "__version__", "")
        except Exception:
            return ""


_DEFAULT_OUTPUT_CANDIDATES = ("/reports", "/loot/reports")


def _default_output_dir() -> str:
    """Pick where rendered docx files should land by default.

    Inside the reporting container, `/reports` maps to
    `<WORK_DIR>/runtime/reports/` on the host — that's where engagement
    deliverables belong. If that mount isn't present (legacy spawn, ad-hoc
    container, host run without docker), fall back to the loot tree so the
    output is at least somewhere recoverable.
    """
    for candidate in _DEFAULT_OUTPUT_CANDIDATES:
        parent = os.path.dirname(candidate) or "/"
        if os.path.isdir(candidate) or os.path.isdir(parent):
            return candidate
    return _DEFAULT_OUTPUT_CANDIDATES[-1]


def _common_dotted_prefix(ids: list[str]) -> str:
    """Return the longest leading dotted segment shared by every id.

    For pwndoc-style ids like `BHI-OFFSEC-25.05.F01`, the project tag
    `BHI-OFFSEC-25.05` is the natural batch filename. Falls back to "" if
    no shared prefix exists at the segment boundary.
    """
    if not ids:
        return ""
    segments_per_id = [str(i).split(".") for i in ids]
    shared: list[str] = []
    for parts in zip(*segments_per_id):
        first = parts[0]
        if all(p == first for p in parts):
            shared.append(first)
        else:
            break
    # Drop the final segment if it looks like a per-finding tag (e.g. F01,
    # 001, VULN-7) — the prefix should describe the project, not the
    # individual finding.
    if shared and len(shared) == len(segments_per_id[0]):
        shared = shared[:-1]
    return ".".join(shared)


class FindingDocxReport(BaseReportSkill):
    """Render one or more findings into a single branded docx via docxtpl.

    The template wraps the finding body in `{%p for finding in findings %}`,
    so each call produces exactly one output file regardless of how many
    findings are supplied. Single-finding renders keep the per-finding
    `{id}-{title}.docx` filename; multi-finding renders derive a project-level
    filename from the common id prefix (or the target).

    Arguments (`run(**kwargs)`):
        finding: dict | None
            A single finding (see module docstring for the expected
            keys). If omitted, `findings` or `findings_path` must be supplied.
        findings: list[dict] | None
            Multiple findings — combined into one docx, one finding per
            page.
        findings_path: str | None
            Path to a YAML or JSON file holding either a single finding
            (`dict`) or a list of findings.
        template_path: str | None
            Override the template location. Defaults to the bundled
            `templates/finding_template.docx`.
        output_dir: str | None
            Directory to write the docx into. Defaults to `/reports` when
            the reporting container's reports mount is present, otherwise
            `/loot/reports`. Created if missing.

    Returns (in the envelope's `findings`):
        {
            "output_path": "/reports/BHI-OFFSEC-25.05-findings-2026-06-10.docx",
            "finding_ids": ["BHI-OFFSEC-25.05.F01", ...],
            "template_path": "/app/templates/finding_template.docx"
        }
    """

    tool = "docxtpl"

    def render(self, **kwargs) -> dict:
        if DocxTemplate is None:
            raise RuntimeError(
                "docxtpl is not installed. Run this skill inside the reporting "
                "container (executors/Dockerfile.reporting) or `uv sync` first."
            )

        raw_findings = self._collect_findings(kwargs)
        if not raw_findings:
            raise ValueError(
                "No findings provided. Pass `finding`, `findings`, or `findings_path`."
            )

        template_path = kwargs.get("template_path") or _default_template_path()
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")

        output_dir = kwargs.get("output_dir") or _default_output_dir()
        os.makedirs(output_dir, exist_ok=True)

        normalized = [_normalize_finding(raw) for raw in raw_findings]

        # Autoescape protects against finding content containing XML
        # specials like `<script>` or `&` — without it docxtpl emits raw
        # text into <w:t> elements and breaks the document.
        jinja_env = _JinjaEnvironment(autoescape=True)

        doc = DocxTemplate(template_path)
        doc.render({"findings": normalized}, jinja_env=jinja_env)

        filename = self._derive_filename(normalized)
        output_path = os.path.join(output_dir, filename)
        doc.save(output_path)
        _rewrite_docx_markdown(output_path)
        self.save_artifact_path(output_path)

        return {
            "output_path": output_path,
            "finding_ids": [f["id"] for f in normalized],
            "template_path": template_path,
        }

    def _derive_filename(self, normalized: list[dict]) -> str:
        # Single-finding renders keep the per-finding naming so one-off
        # deliverables stay self-describing.
        if len(normalized) == 1:
            only = normalized[0]
            return f"{_slugify(only['id'])}-{_slugify(only['title'])}.docx"

        prefix = _common_dotted_prefix([f["id"] for f in normalized])
        if not prefix:
            prefix = _slugify(self.target or "engagement")
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{_slugify(prefix)}-findings-{date}.docx"

    def _collect_findings(self, kwargs: dict) -> list[dict]:
        items: list[dict] = []
        if kwargs.get("finding"):
            items.append(kwargs["finding"])
        if kwargs.get("findings"):
            items.extend(kwargs["findings"])
        if kwargs.get("findings_path"):
            items.extend(self._load_findings_file(kwargs["findings_path"]))
        return items

    @staticmethod
    def _load_findings_file(path: str) -> list[dict]:
        with open(path) as f:
            content = f.read()
        suffix = os.path.splitext(path)[1].lower()
        if suffix in (".yaml", ".yml"):
            import yaml  # PyYAML — pulled in via pyproject.toml

            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        raise ValueError(f"Unsupported findings file shape in {path}")

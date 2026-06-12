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

import json
import os
import re
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

try:
    from docxtpl import DocxTemplate
    from jinja2 import Environment as _JinjaEnvironment
except ImportError:  # Available inside the reporting container and dev venv
    DocxTemplate = None  # type: ignore[assignment]
    _JinjaEnvironment = None  # type: ignore[assignment]


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

"""Dashboard package — Jinja2 environment setup and render helpers."""

import json
import os
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

try:
    from pygments import highlight as _pygments_highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import BashLexer, PythonLexer

    _formatter = HtmlFormatter(style="github-dark", nowrap=True, noclasses=False)
    PYGMENTS_CSS = _formatter.get_style_defs(".hl")
    _LEXERS = {"python": PythonLexer(), "bash": BashLexer(), "shell": BashLexer()}

    def highlight_code(code, language="python"):
        if not code:
            return Markup("")
        lexer = _LEXERS.get(language, PythonLexer())
        return Markup(_pygments_highlight(code, lexer, _formatter))

except ImportError:  # pragma: no cover — pygments is a declared dep
    PYGMENTS_CSS = ""

    def highlight_code(code, language="python"):
        return Markup(escape(code or ""))


_PRETTY_MAX_DEPTH = 12
_PRETTY_INLINE_MAX = 140
_PRETTY_TABLE_MAX_COLS = 8

_SEVERITY_CLASSES = {
    "critical": "pj-sev-critical",
    "high": "pj-sev-high",
    "medium": "pj-sev-medium",
    "low": "pj-sev-low",
    "info": "pj-sev-info",
    "informational": "pj-sev-info",
}

_STATUS_CLASSES = {
    "success": "pj-status-success",
    "ok": "pj-status-success",
    "passed": "pj-status-success",
    "completed": "pj-status-success",
    "true": "pj-status-success",
    "error": "pj-status-error",
    "errored": "pj-status-error",
    "failed": "pj-status-error",
    "failure": "pj-status-error",
    "fail": "pj-status-error",
    "false": "pj-status-error",
    "partial": "pj-status-warn",
    "warning": "pj-status-warn",
    "warn": "pj-status-warn",
    "queued": "pj-status-queued",
    "claimed": "pj-status-queued",
    "running": "pj-status-running",
}

_HTTP_STATUS_KEYS = {
    "status",
    "status_code",
    "http_status",
    "http_code",
    "code",
    "response_code",
    "statuscode",
}

_HTTP_LINE_RE = re.compile(r"(HTTP/[\d.]+) (\d{3})")
_HTTP_HEADER_RE = re.compile(r"(?m)^([A-Za-z][A-Za-z0-9_-]+):")
_MD_HEADER_RE = re.compile(r"(?m)^(#{1,6})[ \t]+(.+)$")
_MD_FENCE_RE = re.compile(r"(?m)^```.*$")
_URL_RE = re.compile(r"(https?://[^\s<>\"')]+)")
_LOG_PREFIX_RE = re.compile(r"(?mi)^(error|warning|warn|info|notice|debug|fatal|critical):")


def _looks_like_url(s: str) -> bool:
    return s.startswith(("http://", "https://")) and " " not in s and "\n" not in s


_JSON_MAX_BYTES = 2_000_000


def _try_parse_structured(s: str):
    """If s is a JSON document or NDJSON, return the parsed value; else None.

    Many security tools emit either a single JSON array/object or one JSON
    object per line (NDJSON, e.g. subfinder, dnsx, naabu). Detecting either
    form lets us render the data as a real list/table instead of as one
    giant escaped string.
    """
    s = s.strip()
    if not s or len(s) > _JSON_MAX_BYTES:
        return None

    if s[0] in "{[":
        try:
            return json.loads(s)
        except (json.JSONDecodeError, ValueError):
            pass

    lines = [ln for ln in s.splitlines() if ln.strip()]
    if len(lines) >= 2 and all(ln.lstrip()[0:1] in "{[" for ln in lines):
        try:
            return [json.loads(ln) for ln in lines]
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def _http_status_class(code: int) -> str | None:
    if 100 <= code <= 599:
        return f"pj-http-{code // 100}xx"
    return None


_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def _inline_md(escaped_line: str) -> str:
    """Apply inline markdown (code, bold, italic, urls) to an already-escaped line."""
    out = _URL_RE.sub(
        r'<a class="pj-link" href="\1" target="_blank" rel="noopener">\1</a>',
        escaped_line,
    )
    out = _INLINE_CODE_RE.sub(r'<code class="md-code">\1</code>', out)
    out = _BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = _ITALIC_RE.sub(r"<em>\1</em>", out)
    return out


def render_analysis(text):
    """Render an LLM interpretation/analysis blob as readable HTML.

    Lightweight markdown: ATX headers (# … ######), unordered/ordered lists,
    fenced code blocks (```), inline code, bold, italic, paragraph breaks,
    and clickable URLs. Unknown content falls through as plain paragraphs.
    """
    if not text:
        return Markup("")

    lines = str(text).splitlines()
    html_parts: list[str] = []
    para_buf: list[str] = []
    list_kind: str | None = None  # 'ul' or 'ol' or None
    in_fence = False
    fence_buf: list[str] = []

    def flush_para():
        if para_buf:
            joined = "<br>".join(_inline_md(escape(line)) for line in para_buf)
            html_parts.append(f'<p class="md-p">{joined}</p>')
            para_buf.clear()

    def flush_list():
        nonlocal list_kind
        if list_kind:
            html_parts.append(f"</{list_kind}>")
            list_kind = None

    def open_list(kind):
        nonlocal list_kind
        if list_kind != kind:
            flush_list()
            cls = "md-ul" if kind == "ul" else "md-ol"
            html_parts.append(f'<{kind} class="{cls}">')
            list_kind = kind

    for raw in lines:
        line = raw.rstrip()

        if in_fence:
            if line.strip().startswith("```"):
                code = "\n".join(fence_buf)
                html_parts.append(f'<pre class="md-pre"><code>{escape(code)}</code></pre>')
                fence_buf = []
                in_fence = False
            else:
                fence_buf.append(raw)
            continue

        if line.strip().startswith("```"):
            flush_para()
            flush_list()
            in_fence = True
            continue

        if not line.strip():
            flush_para()
            flush_list()
            continue

        m_h = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m_h:
            flush_para()
            flush_list()
            level = len(m_h.group(1))
            text_inner = _inline_md(escape(m_h.group(2)))
            html_parts.append(f'<h{level} class="md-h md-h{level}">{text_inner}</h{level}>')
            continue

        m_ul = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if m_ul:
            flush_para()
            open_list("ul")
            html_parts.append(f"<li>{_inline_md(escape(m_ul.group(1)))}</li>")
            continue

        m_ol = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if m_ol:
            flush_para()
            open_list("ol")
            html_parts.append(f"<li>{_inline_md(escape(m_ol.group(1)))}</li>")
            continue

        flush_list()
        para_buf.append(line)

    if in_fence and fence_buf:
        # Unterminated fence — render what we have.
        code = "\n".join(fence_buf)
        html_parts.append(f'<pre class="md-pre"><code>{escape(code)}</code></pre>')
    flush_para()
    flush_list()

    return Markup("".join(html_parts))


def _highlight_pre(escaped: str) -> str:
    """Apply lightweight semantic highlighting to escaped multiline text."""
    out = _URL_RE.sub(
        r'<a class="pj-link" href="\1" target="_blank" rel="noopener">\1</a>',
        escaped,
    )
    out = _HTTP_LINE_RE.sub(
        lambda m: (
            f'<span class="pj-http-proto">{m.group(1)}</span> '
            f'<span class="pj-http-{m.group(2)[0]}xx">{m.group(2)}</span>'
        ),
        out,
    )
    # Log-level prefixes must run before the generic HTTP header regex so
    # that "error:" / "warning:" don't get styled as plain headers.
    out = _LOG_PREFIX_RE.sub(
        lambda m: f'<span class="pj-log-{m.group(1).lower()}">{m.group(1)}</span>:',
        out,
    )
    out = _HTTP_HEADER_RE.sub(r'<span class="pj-http-header">\1</span>:', out)
    out = _MD_HEADER_RE.sub(
        r'<span class="pj-md-h">\1 \2</span>',
        out,
    )
    out = _MD_FENCE_RE.sub(r'<span class="pj-md-fence">\g<0></span>', out)
    return out


def _string_class(value: str, parent_key: str | None) -> str:
    """Pick a semantic CSS class for an inline string based on its value/key."""
    low = value.strip().lower()
    if (parent_key or "").lower() == "severity" and low in _SEVERITY_CLASSES:
        return _SEVERITY_CLASSES[low]
    if low in _SEVERITY_CLASSES and "sever" in (parent_key or "").lower():
        return _SEVERITY_CLASSES[low]
    if low in _STATUS_CLASSES:
        return _STATUS_CLASSES[low]
    return "pj-string"


def pretty_json(value, depth=0, parent_key=None):
    """Render an arbitrary JSON-like value as readable HTML.

    Dicts → key/value list. Lists of dicts → table (when columns fit).
    Multiline strings → code block with HTTP/header/markdown highlighting.
    URLs → links. Severity, status keywords, and HTTP codes get colored
    based on context.
    """
    if depth > _PRETTY_MAX_DEPTH:
        return Markup('<span class="pj-truncated">…</span>')

    if value is None:
        return Markup('<span class="pj-null">—</span>')
    if isinstance(value, bool):
        cls = "pj-status-success" if value else "pj-status-error"
        return Markup(f'<span class="pj-bool {cls}">{str(value).lower()}</span>')
    if isinstance(value, (int, float)):
        extra = ""
        if isinstance(value, int) and (parent_key or "").lower() in _HTTP_STATUS_KEYS:
            http_cls = _http_status_class(value)
            if http_cls:
                extra = f" {http_cls}"
        return Markup(f'<span class="pj-num{extra}">{escape(str(value))}</span>')

    if isinstance(value, str):
        if not value:
            return Markup('<span class="pj-empty">empty</span>')
        if "\n" in value or len(value) > _PRETTY_INLINE_MAX:
            parsed = _try_parse_structured(value)
            if parsed is not None and not isinstance(parsed, (str, int, float, bool)):
                return pretty_json(parsed, depth + 1, parent_key=parent_key)
            return Markup(f'<pre class="pj-text">{_highlight_pre(escape(value))}</pre>')
        if _looks_like_url(value):
            safe = escape(value)
            return Markup(
                f'<a class="pj-link" href="{safe}" target="_blank" rel="noopener">{safe}</a>'
            )
        cls = _string_class(value, parent_key)
        return Markup(f'<span class="{cls}">{escape(value)}</span>')

    if isinstance(value, dict):
        if not value:
            return Markup('<span class="pj-empty">empty</span>')
        rows = []
        for k, v in value.items():
            rows.append(
                f'<dt class="pj-key">{escape(str(k))}</dt>'
                f'<dd class="pj-val">{pretty_json(v, depth + 1, parent_key=str(k))}</dd>'
            )
        return Markup(f'<dl class="pj-dl">{"".join(rows)}</dl>')

    if isinstance(value, (list, tuple)):
        items = list(value)
        if not items:
            return Markup('<span class="pj-empty">empty</span>')

        # Promote homogeneous list-of-dicts to a table when column count is sane.
        if len(items) > 1 and all(isinstance(it, dict) for it in items):
            columns: list[str] = []
            for it in items:
                for k in it.keys():
                    if k not in columns:
                        columns.append(str(k))
            if 0 < len(columns) <= _PRETTY_TABLE_MAX_COLS:
                head = "".join(f"<th>{escape(c)}</th>" for c in columns)
                body = []
                for it in items:
                    cells = "".join(
                        f"<td>{pretty_json(it.get(c), depth + 1, parent_key=c)}</td>"
                        for c in columns
                    )
                    body.append(f"<tr>{cells}</tr>")
                return Markup(
                    f'<table class="pj-table"><thead><tr>{head}</tr></thead>'
                    f'<tbody>{"".join(body)}</tbody></table>'
                )

        list_items = "".join(
            f"<li>{pretty_json(it, depth + 1, parent_key=parent_key)}</li>" for it in items
        )
        return Markup(f'<ul class="pj-list">{list_items}</ul>')

    return Markup(f'<span class="pj-string">{escape(str(value))}</span>')


_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
)
_env.filters["highlight"] = highlight_code
_env.filters["pretty_json"] = pretty_json
_env.filters["analysis"] = render_analysis
_env.globals["pygments_css"] = PYGMENTS_CSS


def _all_engagements():
    """Engagement options for the global scope selector (id + name only)."""
    # Imported lazily so importing the dashboard package doesn't require the DB.
    from state.reporting import list_engagements

    return [{"engagement_id": e["engagement_id"], "name": e["name"]} for e in list_engagements()]


_env.globals["all_engagements"] = _all_engagements


def render(template_name, **context):
    """Render a template to string."""
    return _env.get_template(template_name).render(**context)

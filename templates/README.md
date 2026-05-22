# Document Templates

This directory holds the docxtpl-tagged templates that the **Reporting executor** renders into final deliverables. Each template pairs with one or more `BaseReportSkill` subclasses in `skills/reporting.py`.

The shipping template is `finding_template.docx`, produced from a hand-formatted source docx by `scripts/build_finding_template.py`. Re-run the builder whenever the source layout changes — do not edit `finding_template.docx` by hand, because the next regeneration will overwrite your changes.

## Why docxtpl (and not Pandoc)

Pandoc renders Markdown into a docx using *style inheritance* from a reference document. It cannot fill *into an existing table layout*. Our finding template is a multi-table form (severity / CVSS / category cells; affected-asset cell; description, impact, PoC, remediation sections; references list), so we use [`docxtpl`](https://docxtpl.readthedocs.io/) — Jinja-on-docx — which preserves the source document byte-for-byte and substitutes content into named placeholders.

Net effect: the output opens cleanly in Word **and Google Docs** because there is no custom XML — only the original table the user authored, with placeholder text swapped for finding content.

## How the renderer is used

The reporting executor (`executors/report_operator.py`) invokes `reporting.FindingDocxReport` like any other skill. Templates are mounted in the container at `/app/templates/`, and rendered output is written to `/loot/reports/`.

```python
from skills.reporting import FindingDocxReport

FindingDocxReport(target="example.test").run(
    finding={...},                  # or findings=[...], or findings_path="..."
    template_path="/app/templates/finding_template.docx",   # optional override
    output_dir="/loot/reports",                              # optional override
)
```

## The layout contract

`FindingDocxReport` normalizes finding dicts into the shape the template expects. Required keys:

| Field | Type | Example |
|-------|------|---------|
| `id` | str | `"BHI-OFFSEC-25.05.F01"` |
| `title` | str | `"Reflected XSS in /search query parameter"` |
| `severity` | str | `"Critical"` / `"High"` / `"Medium"` / `"Low"` / `"Info"` |
| `category` | str | `"Web"` / `"API"` / `"Cloud"` / `"Infra"` / etc. |
| `affected` | str | `"https://example.test/search?q="` |
| `description` | str | Single paragraph describing what was found |
| `impact` | str | Single paragraph on the business / technical impact |
| `proof_of_concept` | str | Single paragraph with reproduction steps or a payload |
| `remediation` | str | Single paragraph with concrete remediation steps |

Optional keys:

| Field | Shape | Notes |
|-------|-------|-------|
| `cvss.score` | str | `"7.4"` — also accepts the flat key `cvss_score` |
| `cvss.vector` | str | `"AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N"` — also accepts `cvss_vector` |
| `references` | list[str] | One entry per line; also accepts a single newline-separated string |

Validation lives in `_normalize_finding()` (`skills/reporting.py`). Missing required fields fail loudly with a `ValueError` listing every missing key.

## Writing the content (style contract)

The rendered docx is the **client-facing deliverable**. Write the finding fields for the client's audience, not for the internal pentest team.

- **Plain, succinct language.** Each field should be a few short paragraphs at most. The template's table layout makes long prose look noisy.
- **Do not reference `Findings.md`, `recon-data.md`, `F-NNN` triage IDs, or `§N.M` recon section markers.** Those files are internal working artifacts and are never shared with the client; citing them creates confusion and leaks internal triage state. Ground claims in things the client can verify on their own — URLs, parameters, response headers, screenshots saved under `/loot`.
- **Each field has one job:**
  - `description` — *what* was found. State the affected component, the observed behavior, and the class of issue in one or two sentences.
  - `impact` — *why it matters*, in business or technical terms a non-pentester can grasp. Be specific ("any authenticated user lured to a crafted URL surrenders their session cookie") instead of vague ("severe security impact").
  - `proof_of_concept` — *how to reproduce*. Self-contained — a reader without prior context should be able to follow it. Cite a concrete request, payload, or command sequence.
  - `remediation` — *what to do*. Actionable: "apply output encoding on the `q` parameter and serve a CSP that disallows inline scripts" beats "implement XSS defenses".
- **Severity is final, not a working estimate.** Strip qualifiers like "(pending triage)" before rendering — the deliverable expresses the post-triage judgment.

The same contract lives in the module docstring of `skills/reporting.py` so an LLM inspecting the skill before invocation sees it.

## The autoescape gotcha

docxtpl does **not** XML-escape `{{ var }}` substitutions by default. A finding with `proof_of_concept = "<script>alert(1)</script>"` would otherwise corrupt the docx — the `<` opens an unparsed tag and everything after it is silently dropped by Word.

`FindingDocxReport.render()` passes `DocxTemplate.render()` a Jinja env constructed with `autoescape=True`. This routes every substitution through `markupsafe.escape`, which turns `<`, `>`, and `&` into their XML entities. The output then opens cleanly and shows the literal payload text.

If you write a new reporting skill, **enable autoescape the same way** — security PoCs routinely contain XML-special characters.

## Building a new template from an example docx

The flow is the same one `build_finding_template.py` follows, but with a different example. Pick the steps that apply:

### 1. Inspect the source layout

The builder needs to know exactly which cells and paragraphs to rewrite. Dump the visible structure first:

```python
from docx import Document

doc = Document("/path/to/example.docx")
for ti, t in enumerate(doc.tables):
    for ri, row in enumerate(t.rows):
        for ci, cell in enumerate(row.cells):
            print(f"T{ti}R{ri}C{ci}: {cell.text!r}")
for i, p in enumerate(doc.paragraphs):
    if p.text.strip():
        print(f"P{i}: {p.text!r}")
```

This gives you the canonical "address" of every placeholder. Record them in the builder script.

### 2. Decide the context shape

The dict you pass to `DocxTemplate.render()` is the contract between your skill and the template. Keep it flat (one level of nesting at most) so Jinja tags stay readable: `{{ finding.title }}` is fine, `{{ engagement.findings[0].cvss.vector }}` is a warning sign.

Add new required fields to the normalizer in `skills/reporting.py` (or write a new normalizer for the new skill).

### 3. Write the placeholder substitution

The builder rewrites placeholder text *at the run level* so docxtpl's tag scanner can find the Jinja markers. Run text is the only place a tag is recognized — tags split across runs are silently ignored.

Use the helpers in `scripts/build_finding_template.py` as a starting point:

- `_replace_paragraph_text(paragraph, new_text)` — preserves the first run's formatting (font, color, bold, etc.), drops every other run *and* drops any sibling `w:hyperlink` elements (which would otherwise leave orphan link text behind).
- `_replace_cell_text(cell, new_text)` — collapses a multi-paragraph cell to one paragraph, then calls `_replace_paragraph_text`.
- `_delete_paragraph(paragraph)` — removes a paragraph entirely (use after collapsing multiple source paragraphs into one placeholder).

For repeated rows or repeated paragraphs (e.g. the references list), use docxtpl's paragraph-level loop syntax:

```
{%p for ref in finding.references %}
{{ ref }}
{%p endfor %}
```

Each `{%p ... %}` paragraph is removed from the rendered output; the paragraph(s) between them are repeated once per loop iteration, inheriting the source paragraph's formatting.

### 4. Add a drift check

The builder asserts on **snippets** of the expected source text before it rewrites anything:

```python
expected = {
    4: "A description of what was found",
    5: "The assessment uncovered an SQL injection",
    ...
}
for idx, snippet in expected.items():
    if snippet not in body_paragraphs[idx].text:
        raise RuntimeError(...)
```

This catches the common failure mode where someone tweaks the source docx in Word and shuffles paragraph indices. Always include a drift check — silent corruption of the output is much worse than a loud build failure.

### 5. Smoke-test

Render a known-good finding and visually inspect the output:

```bash
uv run python - <<'PY'
import tempfile, shutil, os
from skills.reporting import FindingDocxReport

sample = {
    "id": "DEMO-001",
    "title": "Smoke test finding",
    "severity": "Info",
    "category": "Demo",
    "cvss": {"score": "0.0", "vector": "AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N"},
    "affected": "n/a",
    "description": "Test render.",
    "impact": "None.",
    "proof_of_concept": "GET /demo?q=<script>alert(1)</script>",
    "remediation": "n/a",
    "references": ["CWE-79"],
}

with tempfile.TemporaryDirectory() as tmp:
    env = FindingDocxReport(target="demo").run(finding=sample, output_dir=tmp)
    print("status:", env["status"], "errors:", env["errors"])
    out = env["artifacts"][0]
    shutil.copy(out, os.path.expanduser("~/Downloads/template_smoketest.docx"))
PY
```

Open the resulting docx in **both** Word and Google Docs and confirm:

- Headings, table widths, fonts, and colors match the source.
- The XSS payload renders as literal text (not as an executed tag or empty cell).
- Multi-entry sections (references, etc.) expand correctly.
- The document opens without "this document needs to be repaired" warnings.

### 6. Register the template

If the template should be the default for a new skill or replace `finding_template.docx`, update:

- `_DEFAULT_TEMPLATE_CANDIDATES` in `skills/reporting.py` if the path changes.
- `executors/Dockerfile.reporting` — the `COPY templates /app/templates` line picks up new templates automatically, but rebuild the container (`make build-reporting`) to make them available inside the agent.
- The builder script's `DEFAULT_SOURCE` / `DEFAULT_OUTPUT` if you want it to be the no-args target.

## Beyond plain text: rich content

The current renderer treats every placeholder as plain text — single paragraph, no inline formatting per substitution. When you need more:

- **Multi-paragraph content**: switch the placeholder to a docxtpl `{%p for ... %}` loop, or pass a `docxtpl.RichText` object that contains line breaks.
- **Inline bold / italic / color**: build a `RichText` object in the skill and pass it as the context value. The XML it injects is trusted by docxtpl, so autoescape is bypassed for that field — only do this with content you generate yourself.
- **Subdocuments (lists, tables, images)**: use docxtpl's `subdoc()` to compose a fragment with python-docx and stitch it into the template at a `{{ var }}` slot.

See the [docxtpl documentation](https://docxtpl.readthedocs.io/en/latest/) for the full feature set. The principle to hold: the template owns the layout; the skill owns the content; the builder script is the bridge between an example docx and the docxtpl form.

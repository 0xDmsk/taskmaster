# Assessment Note-Taking Template

Every Taskmaster engagement should produce two living documents in the **current working directory** (the orchestrator's CWD — i.e. the assessment folder, not `audit/`). They grow across the engagement and are the human-readable counterpart to `audit/session_report.md`:

| File | Purpose |
|---|---|
| `Findings.md` | The findings log. Numbered `F-NNN` entries — vulnerabilities, misconfigurations, design risks, **and informational/positive observations**. The triage-ready output of the engagement. |
| `recon-data.md` | The raw data dossier underlying the findings. Observations only — no exploitation, no payloads beyond benign queries. Findings cite this file by section number. |

These files are **default behavior**. Create them on first observation; do not wait for the user to ask. Append as new evidence lands. Do not rewrite history — if a hypothesis is overturned, leave the original note and add a follow-up paragraph dated with the new observation.

---

## `Findings.md` structure

### Header (write once, update as scope shifts)

```markdown
# {Target} — Findings Log

Engagement: {program / authorization channel}. Scope: {hosts, paths, in-scope assets}. {Note any out-of-scope adjacencies you'll record but not report.}

Source IP geolocates to {region}; verify each cookie/redirect observation from a second egress before reporting externally.

**Coverage note**: this log is weighted toward {area actually probed}. Anything later found outside that focus should be classified as a separate finding, not a contradiction of what's recorded here.
```

### Per-finding entry

Each finding gets its own section. Use `F-NNN` numbering; sub-letters (`F-002A`) for findings closely related to an existing one. Severity is a **working estimate pending triage** — keep it in the title.

```markdown
## F-007 — Short descriptive title (Severity)

**Where**: Exact URL(s), endpoint(s), or file path(s). Include HTTP method when relevant. Cite recon-data.md sections that captured the evidence (e.g. `§4.3`, `§12.15`).

**Observation**: What you saw. Be concrete — paste the response headers, JSON, or HTML excerpt that proves the claim. If multiple probes produced the same result, summarize the corpus (e.g. "73/73 returned 200 anonymously").

**Reproduction** *(omit for purely informational entries with no actionable repro)*:
```bash
curl -s https://target/path
```

**Why it matters**: Concrete impact, not generic theory. Tie it to the product's threat model — what an attacker can do, or what a defender loses, *in this specific surface*. If the impact is conditional ("only matters if X"), say so.

**Status** *(when relevant)*: Confirmed live on {date}; awaiting authed retest; refuted by {observation}; etc.

**Recommendation**: One or two sentences. The fix, or the next investigative step if the finding is still being characterized.
```

### Severity guidance

- Severities are working estimates: `Informational`, `Low`, `Medium`, `High`, `Critical`. Pair with `(potential Medium)` etc. when the upgrade path depends on a future test.
- **Always log positive observations.** "No HSTS preload submitted" is a finding; so is "PII detection rejects the synthetic canary on every refused turn." A clean negative result that took real effort to confirm is worth its own `F-NNN` entry — it documents what the engagement *ruled out*.

### Cross-referencing

Cite the `recon-data.md` sections that produced the evidence using `§{section-number}`. Multiple sections OK: `(§4.1, §12.8)`. Keep the section numbers stable once published — append new sections instead of renumbering.

---

## `recon-data.md` structure

### Header

```markdown
# {Target} — Recon Data

Recon window: {start date/time} – {ongoing or end date/time}
Source: taskmaster agents ({kali / playwright})
Source IP geolocation hint: {region, with evidence — server-returned location code, content-language, etc.}
Authorization channel: {program ref, `/.well-known/security.txt` confirmation, scope doc URL}

This is the data dossier underlying `Findings.md`. It records observations only — no exploitation, no payloads beyond benign queries.
```

### Section taxonomy

Organize by *surface* and *flow*, not by tool used. Number sections so findings can cite them. A typical layout grows like this:

```
1. Surface map
   1.1 Hosts and redirect chains
   1.2 DNS
   1.3 Cert-transparency
2. {Product surface A} — lifecycle
   2.1 Bootstrap
   2.2 Anonymous-friendly endpoints
   2.3 Auth/CSRF gates
   2.4 Canonical request shape
   2.5 Response event taxonomy
   2.6 Post-action endpoints
   2.7 Backend services touched
   ...
3. {Product surface B} — lifecycle
   ...
4. Cross-surface observations (headers, cookies, CSP, etc.)
...
12. Probe transcripts (numbered captures referenced by Findings.md)
   12.1 ...
   12.2 ...
```

Numbering choices:
- Top-level sections are stable areas of the target (a product, an API namespace, a host family). Don't renumber once published.
- Transcripts of individual probes go under a high-numbered "captures" section (e.g. `12.x`) so you can append new ones without disturbing the surface-map numbering.

### Inside each section

- Use **tables** for repetitive structured data (hosts, DNS records, endpoints with status + sample response).
- Paste **raw captures** (HTTP request/response, JSON bodies, SSE frames) in fenced code blocks with the language tag (` ```http`, ` ```json`).
- Use **observations** (prose) to call out what the capture means and what's worth probing next.
- Mark anonymous-vs-authenticated state, source IP, and date when behavior is environment-dependent.

### What goes in here vs. Findings.md

| Belongs in `recon-data.md` | Belongs in `Findings.md` |
|---|---|
| Raw request/response captures | The interpretation of those captures |
| Endpoint shape, parameter taxonomy, event types | "This endpoint trusts a client-echoed URL" |
| DNS/cert/host inventory | "This subdomain is dangling and takeover-able" |
| Negative scans (NXDOMAIN, 404, 401 patterns) | "Scope perimeter confirmed; no staging hosts reachable" |
| Per-turn behavior notes from chat/API testing | A consolidated finding about that behavior |

Rule of thumb: if a teammate asks "what did you actually see," send them to `recon-data.md`. If they ask "what's wrong and what should we fix," send them to `Findings.md`.

---

## Worked excerpt (truncated)

### `Findings.md`

```markdown
## F-002 — HSTS header missing on all origins in scope (Low)

**Where**: `target.com/`, `target.com/app`, `api.target.com/v1/me`. (§4.1, §12.8)

**Observation**: No `strict-transport-security` header on any HTML or JSON response across the 6 paths probed. HSTS preload status not yet confirmed.

**Why it matters**: HTTP→HTTPS is enforced by `upgrade-insecure-requests` in CSP, but a first-visit MITM on a coffee-shop network can still strip TLS for the bootstrap request before CSP applies.

**Recommendation**: Add `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` after subdomain audit, then submit to the HSTS preload list.
```

### `recon-data.md`

```markdown
### 4.1 Security headers (anonymous GET)

| URL | HSTS | CSP | X-Frame-Options |
|---|---|---|---|
| `https://target.com/` | — | `default-src 'self'; ...` | `SAMEORIGIN` |
| `https://target.com/app` | — | (same) | `SAMEORIGIN` |
| `https://api.target.com/v1/me` | — | — (JSON) | — |
```

The cross-ref `(§4.1, §12.8)` in F-002 points the reader straight to the evidence.

---

## When to update

- **After every successful execution** that produced novel data: append a `recon-data.md` section (or extend an existing one) with the captures, then decide whether the data crosses the bar for a `Findings.md` entry.
- **When a hypothesis flips**: leave the original `Findings.md` paragraph in place, add a new paragraph dated with the new observation. Don't silently rewrite history.
- **At engagement wrap-up**: re-read both files end-to-end. Promote anything that's still "potential Medium" to a real severity, or downgrade to Informational if the worst-case didn't materialize.

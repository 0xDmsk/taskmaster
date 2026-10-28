# Shared Findings — Taskmaster reporting on Google Sites

A team-wide replica of Taskmaster's reporting dashboard that colleagues reach
through a Google Site. Everyone adds and edits their own findings, and the
Overview shows the picture across all past engagements.

It is a Google Apps Script web app (UI + logic) backed by a Google Sheet
(storage), embedded in a Google Site. A Google Site can't store data or run
app logic itself; it only frames the web app.

## What's carried over from the Taskmaster dashboard

| Taskmaster page | Shared Findings |
| --- | --- |
| Overview | Overview with an engagement and year filter: stats, findings by severity, pipeline, top categories, latest findings, recently active engagements, findings per contributor |
| Engagements | Same: create form, card grid with severity chips and open counts, plus search and a status filter |
| Engagement workspace | Same: severity and pipeline roll-ups, filterable finding cards with inline status change, scope panel. Plus editing the engagement (name, client, status, summary) and deleting it once it is empty |
| Report finding form | Same fields, evidence and references (add/delete). Plus delete, **Copy as new** (reuse a past finding in another engagement) and who created/edited it |
| — | **All Findings**: a sortable, filterable table across every engagement (by severity, status, category, author, free text) |
| — | **Import from Taskmaster**: upload an export of your local Taskmaster's reporting tables |

Left out because they depend on the local Taskmaster runtime: Executions,
Targets, Agents, Observations, DOCX rendering, threat models, finding templates.

**Collaboration safeguards**
- Every write is attributed to the signed-in Google account (`created_by` / `updated_by`).
- If a colleague saved a finding after you opened it, your save is refused
  instead of overwriting theirs. Your form edits are kept, so you can copy them.
- Writes are serialised with a script lock.
- Destructive buttons need a second click to confirm.

## Setup (about 10 minutes)

1. **Create the Sheet.** Create a new Google Sheet, e.g. "Shared Findings DB".
   Put it in a **Shared Drive** owned by the team, so the data doesn't belong
   to one person's account.
2. **Add the script.** In the Sheet, open **Extensions → Apps Script**. Then:
   - Replace the contents of `Code.gs` with [`Code.gs`](Code.gs).
   - Add three HTML files (**+ → HTML**) named exactly `Index`, `Styles` and
     `App`, and paste in [`Index.html`](Index.html), [`Styles.html`](Styles.html)
     and [`App.html`](App.html).
   - Open **Project Settings**, tick *Show "appsscript.json" manifest file*,
     and replace the manifest with [`appsscript.json`](appsscript.json).
3. **Initialise the tabs.** In the editor, select the `setup` function and click
   **Run**, then grant the permissions. This creates the `engagements`,
   `report_assets`, `findings`, `finding_evidence` and `finding_references` tabs.
4. **Restrict access (recommended).** These are vulnerability details, and
   "anyone in the domain" is the narrowest access a web app can be given. Go to
   **Project Settings → Script properties** and add `ALLOWED_USERS`, a
   comma-separated list of emails and/or `@domain` entries, for example
   `alice@corp.com, bob@corp.com`. People not on the list get an access-denied
   page, and their API calls are refused.
5. **Deploy.** Click **Deploy → New deployment → Web app**, and set:
   - *Execute as:* **Me**. Colleagues write through the script, so the Sheet
     only needs to be shared with the deployer. People can't edit raw rows by
     accident.
   - *Who has access:* **Anyone within <your domain>**.

   Copy the `/exec` URL.
6. **Embed in the Site.** In Google Sites, go to **Insert → Embed → By URL**,
   paste the `/exec` URL, and choose *Whole page*. Drag the embed to full width
   and give it plenty of height (about 1400px or more). Restrict the Site's
   sharing to the same team.

### Updating the code later

Edit the files in the Apps Script editor, then go to **Deploy → Manage
deployments → (edit) → Version: New version**. The `/exec` URL, and so the Site
embed, stays the same. As an alternative to copy-pasting, the folder works with
[`clasp`](https://github.com/google/clasp): `clasp clone <scriptId>`, copy these
files in, then `clasp push`.

## Importing from a local Taskmaster

```bash
# from a Taskmaster checkout / engagement folder
uv run python scripts/export_reporting_json.py -o taskmaster-export.json
uv run python scripts/export_reporting_json.py --engagement eng_abc --engagement eng_def -o export.json
uv run python scripts/export_reporting_json.py --db /path/to/runtime/state/executions.db -o export.json
```

Then upload the file on the **Import from Taskmaster** page.

- Records keep their Taskmaster ids, so re-importing is safe.
- An engagement or finding is only overwritten when the incoming copy is newer
  than the shared copy.
- Evidence and references are never overwritten once they are shared.
- Records with no author (Taskmaster's `system`) are attributed to whoever
  imports them.

## Limits and notes

- **Cell size:** Google Sheets allows about 50,000 characters per cell, and the
  app refuses longer fields. Put big tool output or screenshots in Drive and add
  the link as **evidence** (`kind: screenshot`, URL).
- **Scale:** the client loads the whole dataset once and again after each
  write. That works comfortably up to a few thousand findings. Use **Refresh**
  in the sidebar to pick up colleagues' changes.
- **Formula safety:** values starting with `= + - @` (including markdown `-`
  lists) are written as plain text, never as formulas.
- **Markdown** in Description, Impact, PoC and Remediation is rendered with
  `marked` and sanitised with `DOMPurify`, both loaded from cdnjs.
- **Blank embed in Sites?** Open the `/exec` URL directly first. If that works
  but the embed stays blank, add
  `.setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)` to `doGet()`
  in `Code.gs` and deploy a new version.
- The Sheet is the source of truth. Use its version history for audits or to
  roll back, and *File → Download* for CSV/XLSX.

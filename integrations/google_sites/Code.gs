/**
 * Shared Findings — a team-wide replica of Taskmaster's reporting dashboard
 * (Overview, Engagements, Engagement workspace, Finding editor) that runs as a
 * Google Apps Script web app on top of a Google Sheet and is embedded in a
 * Google Site.
 *
 * Storage: one Sheet tab per Taskmaster reporting table. Column names match
 * Taskmaster's SQLite schema (state/storage.py) so a Taskmaster export
 * (scripts/export_reporting_json.py) imports without translation.
 *
 * Deploy as: Execute as "Me", access "Anyone within <your domain>". The sheet
 * then only needs to be shared with the deployer; colleagues write through this
 * script, and every change is attributed to their signed-in Google account.
 */

const TABLES = {
  engagements: {
    key: 'engagement_id',
    cols: ['engagement_id', 'name', 'client_name', 'status', 'summary',
           'created_at', 'created_by', 'updated_at', 'updated_by'],
  },
  report_assets: {
    key: 'asset_id',
    cols: ['asset_id', 'engagement_id', 'kind', 'value', 'description',
           'created_at', 'created_by', 'updated_at'],
  },
  findings: {
    key: 'finding_id',
    cols: ['finding_id', 'engagement_id', 'title', 'severity', 'category', 'status',
           'affected', 'description', 'impact', 'proof_of_concept', 'remediation',
           'cvss_score', 'cvss_vector', 'source_execution_id',
           'created_at', 'created_by', 'updated_at', 'updated_by'],
  },
  finding_evidence: {
    key: 'evidence_id',
    cols: ['evidence_id', 'finding_id', 'kind', 'title', 'body', 'artifact_path', 'url',
           'sort_order', 'created_at', 'created_by'],
  },
  finding_references: {
    key: 'reference_id',
    cols: ['reference_id', 'finding_id', 'label', 'url', 'sort_order',
           'created_at', 'created_by'],
  },
};

// Mirrors state/reporting.py and dashboard/api.py ordering.
const SEVERITIES = ['Critical', 'High', 'Medium', 'Low', 'Info'];
const STATUSES = ['draft', 'needs_review', 'confirmed', 'reported', 'accepted_risk', 'false_positive'];
const CLOSED_STATUSES = ['reported', 'accepted_risk', 'false_positive'];
const ENGAGEMENT_STATUSES = ['active', 'complete', 'archived'];
const CATEGORIES = ['Web', 'OS-Windows', 'Multi', 'Cloud-AWS', 'API', 'Containers',
  'Infrastructure', 'OS-Multi', 'Cloud-GCP', 'Software', 'Thick-Client', 'ActiveDirectory',
  'OS-Linux', 'Mobile-Android', 'CI-CD', 'Cloud-Azure', 'Okta', 'AI-LLM', 'Other', 'TBD'];
const ASSET_KINDS = ['host', 'url', 'domain', 'network', 'app'];
const EVIDENCE_KINDS = ['note', 'request', 'response', 'screenshot', 'artifact'];

// Google Sheets rejects cells over 50,000 characters.
const MAX_CELL = 49000;

// --------------------------------------------------------------------------- //
// Web app entry points                                                         //
// --------------------------------------------------------------------------- //

function doGet() {
  if (!allowed_()) {
    return HtmlService.createHtmlOutput(
      '<p style="font-family:sans-serif">' + user_() + ' is not on the Shared Findings access list. ' +
      'Ask the site owner to add you.</p>').setTitle('Shared Findings');
  }
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('Shared Findings')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function include(name) {
  return HtmlService.createHtmlOutputFromFile(name).getContent();
}

/**
 * Single RPC endpoint for the client (google.script.run.api). Reads return the
 * full dataset; every write returns the fresh dataset too, so the client always
 * sees colleagues' latest changes after it saves.
 */
function api(action, payload) {
  if (!allowed_()) throw new Error(user_() + ' is not on the Shared Findings access list.');
  payload = payload || {};
  if (action === 'bootstrap') return snapshot_();
  const handler = ACTIONS[action];
  if (!handler) throw new Error('Unknown action: ' + action);
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const result = handler(payload);
    return Object.assign(snapshot_(), { result: result || null });
  } finally {
    lock.releaseLock();
  }
}

const ACTIONS = {
  saveEngagement: saveEngagement_,
  deleteEngagement: deleteEngagement_,
  addAsset: addAsset_,
  deleteAsset: deleteAsset_,
  saveFinding: saveFinding_,
  setFindingStatus: setFindingStatus_,
  deleteFinding: deleteFinding_,
  addEvidence: addEvidence_,
  deleteEvidence: deleteEvidence_,
  addReference: addReference_,
  deleteReference: deleteReference_,
  importTaskmaster: importTaskmaster_,
};

/** Run once from the Apps Script editor: creates and formats the tabs. */
function setup() {
  const ss = ss_();
  Object.keys(TABLES).forEach(function (name) {
    let sh = ss.getSheetByName(name);
    if (!sh) sh = ss.insertSheet(name);
    const cols = TABLES[name].cols;
    const have = sh.getLastColumn() ? headers_(sh) : [];
    const missing = cols.filter(function (c) { return have.indexOf(c) < 0; });
    if (missing.length) {
      sh.getRange(1, have.length + 1, 1, missing.length).setValues([missing]);
    }
    // Plain-text everywhere: stops Sheets turning ISO timestamps into dates
    // and CVSS scores like "7.50" into numbers.
    sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns()).setNumberFormat('@');
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, sh.getLastColumn()).setFontWeight('bold');
  });
  const stray = ss.getSheetByName('Sheet1');
  if (stray && stray.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(stray);
}

// --------------------------------------------------------------------------- //
// Engagements & scope                                                          //
// --------------------------------------------------------------------------- //

function saveEngagement_(p) {
  const name = str_(p.name).trim();
  if (!name) throw new Error('Engagement name is required.');
  const status = p.status ? oneOf_(p.status, ENGAGEMENT_STATUSES, 'status') : 'active';
  const now = now_();
  const fields = {
    name: name,
    client_name: str_(p.client_name).trim(),
    status: status,
    summary: str_(p.summary),
    updated_at: now,
    updated_by: user_(),
  };
  if (p.engagement_id) {
    const current = getRow_('engagements', p.engagement_id);
    checkFresh_(current, p.expected_updated_at, 'engagement');
    return updateRow_('engagements', p.engagement_id, fields);
  }
  return insertRow_('engagements', Object.assign(fields, {
    engagement_id: newId_('eng'),
    created_at: now,
    created_by: user_(),
  }));
}

function deleteEngagement_(p) {
  const id = str_(p.engagement_id);
  getRow_('engagements', id);
  const findings = readTable_('findings').filter(function (f) { return f.engagement_id === id; });
  if (findings.length) {
    throw new Error('Move or delete its ' + findings.length + ' finding(s) before deleting this engagement.');
  }
  deleteWhere_('report_assets', function (a) { return a.engagement_id === id; });
  deleteWhere_('engagements', function (e) { return e.engagement_id === id; });
}

function addAsset_(p) {
  getRow_('engagements', p.engagement_id);
  const value = str_(p.value).trim();
  if (!value) throw new Error('Scope value is required.');
  const now = now_();
  return insertRow_('report_assets', {
    asset_id: newId_('asset'),
    engagement_id: p.engagement_id,
    kind: oneOf_(p.kind || 'host', ASSET_KINDS, 'kind'),
    value: value,
    description: str_(p.description).trim(),
    created_at: now,
    created_by: user_(),
    updated_at: now,
  });
}

function deleteAsset_(p) {
  deleteWhere_('report_assets', function (a) { return a.asset_id === p.asset_id; });
}

// --------------------------------------------------------------------------- //
// Findings, evidence, references                                               //
// --------------------------------------------------------------------------- //

function saveFinding_(p) {
  const title = str_(p.title).trim();
  if (!title) throw new Error('Finding title is required.');
  if (p.engagement_id) getRow_('engagements', p.engagement_id);
  const now = now_();
  const fields = {
    engagement_id: str_(p.engagement_id),
    title: title,
    severity: oneOf_(p.severity || 'Info', SEVERITIES, 'severity'),
    category: CATEGORIES.indexOf(p.category) >= 0 ? p.category : (p.category ? 'Other' : 'TBD'),
    status: oneOf_(p.status || 'draft', STATUSES, 'status'),
    affected: str_(p.affected),
    description: str_(p.description),
    impact: str_(p.impact),
    proof_of_concept: str_(p.proof_of_concept),
    remediation: str_(p.remediation),
    cvss_score: str_(p.cvss_score).trim(),
    cvss_vector: str_(p.cvss_vector).trim(),
    source_execution_id: str_(p.source_execution_id).trim(),
    updated_at: now,
    updated_by: user_(),
  };
  if (p.finding_id) {
    const current = getRow_('findings', p.finding_id);
    checkFresh_(current, p.expected_updated_at, 'finding');
    return updateRow_('findings', p.finding_id, fields);
  }
  return insertRow_('findings', Object.assign(fields, {
    finding_id: newId_('fnd'),
    created_at: now,
    created_by: user_(),
  }));
}

function setFindingStatus_(p) {
  const current = getRow_('findings', p.finding_id);
  checkFresh_(current, p.expected_updated_at, 'finding');
  return updateRow_('findings', p.finding_id, {
    status: oneOf_(p.status, STATUSES, 'status'),
    updated_at: now_(),
    updated_by: user_(),
  });
}

function deleteFinding_(p) {
  const id = str_(p.finding_id);
  getRow_('findings', id);
  deleteWhere_('finding_evidence', function (e) { return e.finding_id === id; });
  deleteWhere_('finding_references', function (r) { return r.finding_id === id; });
  deleteWhere_('findings', function (f) { return f.finding_id === id; });
}

function addEvidence_(p) {
  getRow_('findings', p.finding_id);
  const url = optionalUrl_(p.url);
  if (!str_(p.title).trim() && !str_(p.body).trim() && !url && !str_(p.artifact_path).trim()) {
    throw new Error('Evidence needs at least a title, body, URL or artifact path.');
  }
  const siblings = readTable_('finding_evidence').filter(function (e) { return e.finding_id === p.finding_id; });
  return insertRow_('finding_evidence', {
    evidence_id: newId_('evd'),
    finding_id: p.finding_id,
    kind: oneOf_(p.kind || 'note', EVIDENCE_KINDS, 'kind'),
    title: str_(p.title).trim(),
    body: str_(p.body),
    artifact_path: str_(p.artifact_path).trim(),
    url: url,
    sort_order: String(siblings.length),
    created_at: now_(),
    created_by: user_(),
  });
}

function deleteEvidence_(p) {
  deleteWhere_('finding_evidence', function (e) { return e.evidence_id === p.evidence_id; });
}

function addReference_(p) {
  getRow_('findings', p.finding_id);
  const url = optionalUrl_(p.url);
  if (!url) throw new Error('Reference URL is required.');
  const siblings = readTable_('finding_references').filter(function (r) { return r.finding_id === p.finding_id; });
  return insertRow_('finding_references', {
    reference_id: newId_('ref'),
    finding_id: p.finding_id,
    label: str_(p.label).trim(),
    url: url,
    sort_order: String(siblings.length),
    created_at: now_(),
    created_by: user_(),
  });
}

function deleteReference_(p) {
  deleteWhere_('finding_references', function (r) { return r.reference_id === p.reference_id; });
}

// --------------------------------------------------------------------------- //
// Import from a local Taskmaster (scripts/export_reporting_json.py)            //
// --------------------------------------------------------------------------- //

/**
 * Upsert a Taskmaster export. Records are matched by their Taskmaster ids, so
 * re-importing the same engagement is safe: a shared row that was edited more
 * recently than the incoming one is kept, everything else is added/refreshed.
 */
function importTaskmaster_(p) {
  let data;
  try {
    data = typeof p.json === 'string' ? JSON.parse(p.json) : p.json;
  } catch (e) {
    throw new Error('Not valid JSON: ' + e.message);
  }
  if (!data || data.format !== 'taskmaster-reporting-export') {
    throw new Error('Not a Taskmaster reporting export (run scripts/export_reporting_json.py).');
  }
  const me = user_();
  const now = now_();
  const author = function (v) { return /@/.test(str_(v)) ? str_(v) : me; };
  const fix = {
    engagements: function (r) {
      r.status = ENGAGEMENT_STATUSES.indexOf(r.status) >= 0 ? r.status : 'active';
      r.created_by = author(r.created_by);
      r.updated_by = author(r.updated_by);
      return r;
    },
    report_assets: function (r) { r.created_by = author(r.created_by); return r; },
    findings: function (r) {
      r.severity = SEVERITIES.indexOf(r.severity) >= 0 ? r.severity : 'Info';
      r.status = STATUSES.indexOf(r.status) >= 0 ? r.status : 'draft';
      r.category = CATEGORIES.indexOf(r.category) >= 0 ? r.category : 'Other';
      r.created_by = author(r.created_by);
      r.updated_by = author(r.updated_by);
      return r;
    },
    finding_evidence: function (r) {
      r.url = /^https?:\/\//i.test(str_(r.url)) ? r.url : '';
      r.created_by = author(r.created_by);
      return r;
    },
    finding_references: function (r) {
      r.created_by = author(r.created_by);
      return /^https?:\/\//i.test(str_(r.url)) ? r : null;
    },
  };
  const counts = {};
  Object.keys(TABLES).forEach(function (table) {
    const incoming = (data[table] || []).map(function (r) {
      return fix[table](Object.assign({ created_at: now, updated_at: now }, r));
    }).filter(Boolean);
    counts[table] = upsertMany_(table, incoming);
  });
  return counts;
}

function upsertMany_(table, records) {
  const sh = sheet_(table);
  const header = headers_(sh);
  const key = TABLES[table].key;
  const keyIdx = header.indexOf(key);
  const updIdx = header.indexOf('updated_at');
  const last = sh.getLastRow();
  // Re-escape existing cells too: the whole range is written back below.
  const rows = last > 1
    ? sh.getRange(2, 1, last - 1, header.length).getValues()
      .map(function (r) { return r.map(function (c) { return safe_(cell_(c)); }); })
    : [];
  const index = {};
  rows.forEach(function (r, i) { index[String(r[keyIdx])] = i; });
  const stats = { added: 0, updated: 0, kept: 0 };
  records.forEach(function (rec) {
    const id = str_(rec[key]);
    if (!id) return;
    const at = index[id];
    if (at === undefined) {
      index[id] = rows.length;
      rows.push(toRow_(header, rec));
      stats.added++;
    } else if (updIdx < 0 || cell_(rows[at][updIdx]) >= str_(rec.updated_at)) {
      // Evidence/references have no updated_at: once shared, the shared copy wins.
      stats.kept++;
    } else {
      rows[at] = toRow_(header, Object.assign(rowToObj_(header, rows[at]), rec));
      stats.updated++;
    }
  });
  if (rows.length) {
    sh.getRange(2, 1, rows.length, header.length).setNumberFormat('@').setValues(rows);
  }
  return stats;
}

// --------------------------------------------------------------------------- //
// Sheet access                                                                 //
// --------------------------------------------------------------------------- //

function snapshot_() {
  const out = {
    user: user_(),
    options: {
      severities: SEVERITIES,
      statuses: STATUSES,
      closed_statuses: CLOSED_STATUSES,
      engagement_statuses: ENGAGEMENT_STATUSES,
      categories: CATEGORIES,
      asset_kinds: ASSET_KINDS,
      evidence_kinds: EVIDENCE_KINDS,
    },
  };
  Object.keys(TABLES).forEach(function (t) { out[t] = readTable_(t); });
  return out;
}

function ss_() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  return id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActiveSpreadsheet();
}

function sheet_(table) {
  const sh = ss_().getSheetByName(table);
  if (!sh) throw new Error('Missing sheet "' + table + '" — run setup() once from the Apps Script editor.');
  return sh;
}

function headers_(sh) {
  return sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String);
}

function readTable_(table) {
  const sh = sheet_(table);
  const header = headers_(sh);
  const last = sh.getLastRow();
  if (last < 2) return [];
  const keyIdx = header.indexOf(TABLES[table].key);
  return sh.getRange(2, 1, last - 1, header.length).getValues()
    .filter(function (r) { return r[keyIdx] !== ''; })
    .map(function (r) { return rowToObj_(header, r); });
}

function rowToObj_(header, row) {
  const o = {};
  header.forEach(function (h, i) { if (h) o[h] = cell_(row[i]); });
  return o;
}

function toRow_(header, obj) {
  return header.map(function (h) { return safe_(obj[h]); });
}

/** Locate a row by primary key; returns { sh, header, rowNum, obj } or throws. */
function locate_(table, id) {
  const sh = sheet_(table);
  const header = headers_(sh);
  const keyIdx = header.indexOf(TABLES[table].key);
  const last = sh.getLastRow();
  if (id && last > 1) {
    const ids = sh.getRange(2, keyIdx + 1, last - 1, 1).getValues();
    for (let i = 0; i < ids.length; i++) {
      if (String(ids[i][0]) === String(id)) {
        const rowNum = i + 2;
        const obj = rowToObj_(header, sh.getRange(rowNum, 1, 1, header.length).getValues()[0]);
        return { sh: sh, header: header, rowNum: rowNum, obj: obj };
      }
    }
  }
  throw new Error('Not found (' + table + ' ' + id + '). It may have been deleted by a colleague — refresh.');
}

function getRow_(table, id) {
  return locate_(table, id).obj;
}

function insertRow_(table, obj) {
  const sh = sheet_(table);
  const header = headers_(sh);
  const rowNum = sh.getLastRow() + 1;
  sh.getRange(rowNum, 1, 1, header.length).setNumberFormat('@').setValues([toRow_(header, obj)]);
  return obj;
}

function updateRow_(table, id, fields) {
  const loc = locate_(table, id);
  const merged = Object.assign(loc.obj, fields);
  loc.sh.getRange(loc.rowNum, 1, 1, loc.header.length).setNumberFormat('@')
    .setValues([toRow_(loc.header, merged)]);
  return merged;
}

function deleteWhere_(table, predicate) {
  const sh = sheet_(table);
  const header = headers_(sh);
  const last = sh.getLastRow();
  if (last < 2) return 0;
  const rows = sh.getRange(2, 1, last - 1, header.length).getValues();
  let n = 0;
  // Bottom-up so earlier row numbers stay valid.
  for (let i = rows.length - 1; i >= 0; i--) {
    if (predicate(rowToObj_(header, rows[i]))) {
      sh.deleteRow(i + 2);
      n++;
    }
  }
  return n;
}

// --------------------------------------------------------------------------- //
// Helpers                                                                      //
// --------------------------------------------------------------------------- //

/** Optimistic concurrency: refuse to overwrite a colleague's newer save. */
function checkFresh_(current, expected, noun) {
  if (expected && current.updated_at && current.updated_at !== expected) {
    throw new Error('This ' + noun + ' was changed by ' + (current.updated_by || 'someone') +
      ' at ' + current.updated_at.slice(0, 16).replace('T', ' ') +
      ' after you opened it. Copy your edits, refresh, and re-apply them.');
  }
}

function cell_(v) {
  if (v instanceof Date) return v.toISOString();
  v = v === null || v === undefined ? '' : String(v);
  // Undo the quote-prefix written by safe_() if Sheets kept it literally.
  return /^'[=+\-@]/.test(v) ? v.slice(1) : v;
}

function safe_(v) {
  v = v === null || v === undefined ? '' : String(v);
  if (v.length > MAX_CELL) {
    throw new Error('A field is ' + v.length + ' characters; Google Sheets allows ' + MAX_CELL +
      '. Move long output into an evidence URL (e.g. a Drive file).');
  }
  // Leading = + - @ would be parsed as a formula (and "- item" markdown lists
  // would break); a quote prefix forces plain text.
  return /^[=+\-@]/.test(v) ? "'" + v : v;
}

function str_(v) {
  return v === null || v === undefined ? '' : String(v);
}

function oneOf_(v, allowed, field) {
  if (allowed.indexOf(v) < 0) throw new Error('Invalid ' + field + ': ' + v);
  return v;
}

function optionalUrl_(v) {
  v = str_(v).trim();
  if (v && !/^https?:\/\//i.test(v)) throw new Error('URLs must start with http:// or https://');
  return v;
}

/**
 * Optional team allowlist (web-app access can only be narrowed to a whole
 * domain). Script property ALLOWED_USERS: comma-separated emails and/or
 * "@domain" entries. Unset = everyone the deployment's access setting admits.
 */
function allowed_() {
  const raw = PropertiesService.getScriptProperties().getProperty('ALLOWED_USERS');
  if (!raw) return true;
  const me = user_().toLowerCase();
  return raw.split(',').map(function (s) { return s.trim().toLowerCase(); }).filter(Boolean)
    .some(function (entry) {
      return entry.charAt(0) === '@' ? me.slice(-entry.length) === entry : me === entry;
    });
}

function user_() {
  return Session.getActiveUser().getEmail() || 'unknown';
}

function now_() {
  return new Date().toISOString();
}

function newId_(prefix) {
  return prefix + '_' + Utilities.getUuid().replace(/-/g, '');
}

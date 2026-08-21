# Mobile Worker

A dedicated Taskmaster executor for mobile application testing. It is the fourth
worker type alongside Kali, Playwright, and Reporting, and follows the same
queue → claim → execute → envelope contract.

- **Image:** `mobile-operator` (`executors/Dockerfile.mobile`)
- **Operator:** `executors/mobile_operator.py`
- **Action type claimed:** `mobile_skill` (only)
- **Skill base:** `skills/mobile_base.py:BaseMobileSkill`
- **Skills:** `skills/mobile.py`
- **`agent_type` for `spawn_agent`:** `"mobile"`

It is delivered in two phases. **Phase 1 (static analysis) is built and
shipping.** Phase 2 (dynamic instrumentation) is designed-for but deferred — see
the roadmap at the end.

---

## Phase 1 — static analysis (shipping)

Headless static analysis of Android APKs. No device, no emulator, no
frida-server — it builds and runs in a plain container, including on Apple
Silicon macOS.

### What's in the image

| Tool | Version pin | Purpose |
|------|-------------|---------|
| `apktool` | `2.9.3` (build ARG) | Decode APK → manifest, resources, smali |
| `jadx` | `1.5.0` (build ARG) | DEX → Java decompiler (available for manual/source review) |
| `nuclei` | latest linux/arm64 (resolved at build) | File-protocol scanning of decompiled trees |
| mobile-nuclei-templates | `optiv/mobile-nuclei-templates` (git clone) | Mobile rule set, at `/opt/mobile-nuclei-templates` (`MOBILE_NUCLEI_TEMPLATES`) |
| headless JRE | Debian `default-jre-headless` | Runtime for apktool + jadx |

To bump apktool/jadx, pass build args:
`docker build --build-arg APKTOOL_VERSION=2.10.0 ...` (or edit the Makefile call).

### Skills

All skills take the APK by **container path** and write artifacts to `/loot`.

| Skill | Key args | Output (`findings`) |
|-------|----------|---------------------|
| `mobile.ApkDecompile` | `apk`, `resources_only=false`, `output_dir?` | `output_dir`, `file_count` |
| `mobile.ManifestScan` | `apk` | `package`, `sdk{min,target}`, `application_flags`, `permissions`, `custom_permissions`, `exported_components`, `deeplinks`, `risk_notes` |
| `mobile.SecretScan` | `source_dir?` **or** `apk` | `secret_matches[]` (redacted), `endpoints[]`, `files_scanned` |
| `mobile.MobileNucleiScan` | `source_dir?` **or** `apk`, `first_party?`, `first_party_depth?`, `package?`, `timeout?`, `concurrency?`, `severity?`, `template_timeout?`, `templates?`, `extra_args?` | `results[]` (template_id, severity, matched), `first_party`, `scope`, `timed_out` |

Notes on behavior:

- **`ManifestScan`** decodes with `-s` (skips smali) for speed. Exported-component
  detection is a heuristic: an explicit `android:exported` wins; otherwise the
  presence of an `<intent-filter>` is treated as exported. Provider defaults vary
  by `targetSdk`, so flagged providers should be confirmed manually (this caveat
  is emitted in `findings.notes`). SDK versions are read from `apktool.yml`.
- **`SecretScan`** works on an already-decompiled tree (`source_dir`, e.g. the
  output of `ApkDecompile`) or decodes the APK itself when given `apk`. Sensitive
  matches (Google keys, JWTs, generic secret assignments) are redacted in output;
  low-sensitivity prefixes (AWS access-key IDs, Firebase URLs) are shown in full.
- **`MobileNucleiScan`** takes the same `source_dir`-or-`apk` input as
  `SecretScan`, and runs nuclei in **file mode (`-file`)** — mandatory for
  file-protocol templates over a source tree; without it nuclei aborts with
  "no templates provided for scan". Verified against nuclei v3.11.

### Recommended: the `mobile-static-assessment` playbook

For a coverage-first pass, don't hand-assemble the skills — run the built-in
playbook so nothing is skipped:

```jsonc
// APK dropped in ./session/ (one .apk); target is a nominal label.
{ "tool": "request_playbook",
  "arguments": { "playbook": "mobile-static-assessment",
                 "target": "com.example.app" } }
```

It expands into a dependency chain (each step runs after the previous COMPLETES):

1. `ManifestScan` (reconnaissance) — manifest triage.
2. `ApkDecompile` (enumeration) — decode once into `/loot/mobile-assessment`,
   reused by the rest so the APK is decompiled a single time.
3. `SecretScan` (enumeration) — secrets across the **whole** tree, including
   `res/values/strings.xml` (the resource findings the first-party nuclei pass
   intentionally skips).
4. `MobileNucleiScan` `first_party=true` (enumeration) — fast, high-signal pass
   over the app's own code.
5. `MobileNucleiScan` full-tree, `timeout=600` (enumeration) — library/SDK and
   resource coverage the first-party pass omits; returns bounded partial results
   if it hits the wall clock.

This deliberately runs **both** nuclei passes so you get guaranteed app-code
coverage *and* a best-effort full-tree sweep — the two together close the
coverage gap that either alone leaves (see "Coverage & what you can miss").

**APK auto-discovery:** every mobile skill, given no `apk`, finds a single `.apk`
under `/session` (then `/loot`) — which is why the playbook's empty-argument steps
just work. Drop exactly one APK in the agent's `session_dir`. Two or more APKs in
the same location is an error (pass `arguments.apk` to disambiguate).

### Coverage & what you can miss

Static scanning is triage, not proof, and some options trade coverage for speed —
know the gaps:

- **`first_party=true` skips third-party/SDK code and most of `res/`.** Real bugs
  live in bundled SDKs and in `res/values`/`res/raw`; a first-party-only run
  misses them. The playbook compensates by also running `SecretScan` over the full
  tree and a full-tree nuclei pass — so use the playbook, or run a full pass
  yourself, rather than relying on first-party alone.
- **A `timed_out: true` result is a floor, not a ceiling.** Files/templates not
  reached before the deadline are silently unscanned. Re-run deeper
  (`first_party_depth`) or longer (`timeout`); never treat a timed-out scan as a
  clean bill.
- **nuclei is a ~42-template pattern matcher.** It flags indicators (a WebView
  with JS enabled), not confirmed vulns, and finds nothing outside those patterns
  — no business logic, crypto misuse, or native `.so` analysis. Treat every match
  as a lead for manual review (jadx is in the image) and eventual dynamic testing.

### Long-running nuclei scans

A decompiled app is thousands of text files, and nuclei's cost scales with
(files × templates), so a large app can run for many minutes. The scan is
**bounded and never open-ended**:

- `timeout` (default **300s**) is a hard wall-clock. nuclei streams matches to
  its JSONL output as it runs, so on timeout the skill returns the **partial
  results found so far** with `findings.timed_out = true` and a note — it does
  not hang or discard work.
nuclei's cost scales with **(files × templates)**, and — measured — raising
concurrency/bulk-size does **not** speed a file scan (over-tuning actually slows
it via parallelism overhead). **The only reliable lever is cutting files:**

- **`first_party=true` is the primary lever.** A real app's decompiled smali is
  mostly framework/third-party code (androidx, kotlin, Google libs) — slow and
  low-signal. First-party mode scopes the scan (via a nuclei `-l` list file) to
  the app's own package smali — derived from the manifest — plus the manifest and
  `res/xml` (network-security-config, FileProvider paths, etc.). It deliberately
  excludes the rest of `res/` (drawables/layouts/values), which on a real app is
  thousands of non-code files that dominate the runtime. Result: far fewer files,
  finishes sooner, and the matches are the app's own code, not library noise.
- **`first_party_depth`** narrows further (default 2 = `com/example`; 3 =
  `com/example/feature`), or set `package` explicitly. If no first-party smali is
  found (heavy obfuscation), it falls back to a full scan and says so in `scope`.
- **`timeout`** — raise it to let a large first-party codebase finish; a very
  large app's own smali can still exceed the default 300s, in which case you get
  bounded partial results and can re-run deeper or longer. Don't push `timeout`
  past ~2h — the reaper force-fails a heartbeat-less execution around there. For
  a scan that genuinely won't fit, **shard it with `request_batch`** instead (see
  below).

**Sharding a full scan that won't fit (`request_batch`).** For a comprehensive
nuclei pass that exceeds the window even scoped, split it by template group into
bounded shards against the one target (`sequential: true`, since same-target work
serializes on the per-target lock). Each shard is a fresh sub-window execution, so
the whole scan completes across shards with per-shard progress and resilience, and
it sidesteps the reaper's ~2h/4h ceilings:

```jsonc
{ "tool": "request_batch",
  "arguments": {
    "target": "com.example.app", "phase": "enumeration", "agent_role": "enumeration",
    "action_type": "mobile_skill", "skill": "mobile.MobileNucleiScan",
    "arguments": { "source_dir": "/loot/mobile-assessment" },
    "sequential": true,
    "shards": [
      { "label": "android", "arguments": { "templates": "/opt/mobile-nuclei-templates/Android" } },
      { "label": "keys",    "arguments": { "templates": "/opt/mobile-nuclei-templates/Keys" } }
    ],
    "justification": "Split the full nuclei template set into bounded per-group shards so the scan completes across sub-window executions instead of one that never fits.",
    "expected_output": "Per-template-group nuclei matches across the app." } }
```
- `severity` cuts template volume (`"medium,high,critical"`) — but drops the
  info/low signatures (WebView usage, JS interfaces, etc.) you often want.
- `concurrency` (default 25 = nuclei's default) and `template_timeout` (5s) are
  tunable but are **not** effective performance levers here — don't reach for them.

**Interaction with `wait_for_completion`:** its default timeout is deliberately
below the MCP client's transport window, so a scan longer than that returns a
re-invokable `TIMEOUT` rather than killing the client connection. Just call
`wait_for_completion` again to keep waiting — the execution keeps running in the
worker. After it completes, attach your analysis with `mark_execution_complete`
(`interpretation=...`); that now works even though the worker already moved the
execution to COMPLETED.

**Input contract (uniform across all four skills):** every skill accepts `apk`
(a container path). The tree-scanning skills — `SecretScan` and
`MobileNucleiScan` — additionally accept `source_dir` to reuse an existing
decompiled tree (e.g. `ApkDecompile`'s `output_dir`); `source_dir` wins when
both are given, otherwise they decode the `apk` themselves. Passing `source_dir`
avoids decompiling twice when you've already run `ApkDecompile`.

### Getting an APK to the worker

APKs are inputs, so drop them in the read-only session mount rather than pasting
anything into a tool call:

1. Put the APK in a folder, e.g. `./session/app.apk`.
2. `spawn_agent` with `agent_type: "mobile"` and `session_dir` set to the
   **absolute** host path of that folder (mounts read-only at `/session`).
3. Point skills at the container path: `arguments.apk = "/session/app.apk"`.

Artifacts (decompiled trees, JSON reports) land in `/loot` → host `runtime/loot/`.

### End-to-end example

```jsonc
// 1. Provision the worker (APK sits in ./session/, resolved to an absolute path)
{ "tool": "spawn_agent",
  "arguments": { "agent_type": "mobile", "target": "com.example.app",
                 "session_dir": "/abs/path/engagement/session" } }

// 2. Manifest triage — first action on a new target, so phase = reconnaissance
{ "tool": "request_security_action",
  "arguments": { "target": "com.example.app", "phase": "reconnaissance",
                 "action_type": "mobile_skill", "skill": "mobile.ManifestScan",
                 "arguments": { "apk": "/session/app.apk" } } }

// 3. Full decompile (phase advances to enumeration), then chain SecretScan +
//    nuclei off its output_dir
{ "tool": "request_security_action",
  "arguments": { "target": "com.example.app", "phase": "enumeration",
                 "action_type": "mobile_skill", "skill": "mobile.ApkDecompile",
                 "arguments": { "apk": "/session/app.apk" } } }
```

Phase follows the standard per-target order (`reconnaissance → enumeration → …`);
a brand-new target starts at `reconnaissance`, so queue the first mobile action
there and advance to `enumeration` for follow-ups.

`SecretScan` / `MobileNucleiScan` take the `output_dir` from `ApkDecompile` as
their `source_dir` (wire it with `depends_on`, or run `SecretScan` with `apk`
directly to let it decode on its own).

### Build & test

```bash
make build-mobile                       # build the image
uv run pytest tests/unit/test_mobile_skills.py tests/unit/test_spawn_agent.py
```

---

## Constraints (why Phase 1 is static-only)

Mobile *dynamic* testing needs a device or emulator, and the host here is Apple
Silicon macOS running Docker Desktop:

- **Emulator inside the container** needs KVM acceleration; Docker Desktop on
  macOS runs in a Linux VM with no nested virtualization — effectively a
  non-starter.
- **Physical device over USB** — Docker Desktop on macOS cannot pass USB through
  to a container.
- **Therefore any dynamic worker must reach a device _over the network_**
  (`adb connect`, `frida -H`), where the device lives outside the container.

There is no self-contained dynamic mobile container on this hardware; that is a
Docker-Desktop-on-macOS limitation, not a Taskmaster one.

iOS is out of scope for both phases: jailbreak-detection bypass and IPA patching
need a jailbroken device plus macOS host tooling, with no container path.

---

## Phase 2 — dynamic instrumentation (roadmap, not built)

Deferred until a networked device source exists. Nothing below is implemented.

**Prerequisite:** a device reachable over the network — a rooted Android
emulator on a Linux+KVM host (`adb connect host:5555`), or a corporate device
farm / cloud device service.

**Planned additions (layered onto the Phase 1 image, not a rewrite):**

1. **Image:** add `frida-tools`, `objection`, `adb`; a `DEVICE_HOST` env var; an
   entrypoint that runs `adb connect $DEVICE_HOST` / targets `frida -H`.
2. **Skill base:** `BaseMobileDynamicSkill` (alongside `BaseMobileSkill`) that
   asserts device connectivity before running and emits the same envelope.
3. **New action type:** `mobile_dynamic_skill`, claimed by the same operator;
   add it to the operator's `SUPPORTED_ACTION_TYPES` and to the Kali operator's
   skip list.
4. **Skills** driving MMSF's curated `Frida_Scripts/*` as script files (the one
   genuinely reusable MMSF asset): SSL-pinning bypass, root/jailbreak-detection
   bypass, plus objection-driven runtime data-storage inspection.

**Explicitly not planned:** wrapping MMSF's interactive REPL (incompatible with
Taskmaster's fire-and-forget execution model), an in-container emulator on macOS,
or any iOS dynamic path.

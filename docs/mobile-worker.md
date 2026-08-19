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
| `mobile.MobileNucleiScan` | `source_dir`, `templates?`, `extra_args?` | `results[]` (template_id, severity, matched) |

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
- **`MobileNucleiScan`** runs nuclei in **file mode (`-file`)** — mandatory for
  file-protocol templates over a source tree; without it nuclei aborts with
  "no templates provided for scan". Verified against nuclei v3.11.

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

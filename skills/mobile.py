"""
Mobile static-analysis skills (Phase 1 — no device required).

Each skill takes an APK by *container* path (an APK dropped in the read-only
`/session` mount, or written under `/loot`) and produces observations plus
artifacts in `/loot`. The logic mirrors what MMSF's manifest/scan modules do,
but headless: no interactive REPL, no device, no frida.

Skills:
  * ApkDecompile     — apktool decode (manifest + resources + smali) to /loot
  * ManifestScan     — parse AndroidManifest.xml for the usual misconfigurations
  * SecretScan       — regex sweep of the decompiled tree for hardcoded secrets
  * MobileNucleiScan — run the mobile nuclei template set over a decompiled tree
"""

import json
import os
import re
import xml.etree.ElementTree as ET

from skills.mobile_base import BaseMobileSkill

ANDROID_NS = "http://schemas.android.com/apk/res/android"


def _android_attr(elem, name):
    return elem.get(f"{{{ANDROID_NS}}}{name}")


def _safe_stem(path: str) -> str:
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    return re.sub(r"[^A-Za-z0-9._-]", "_", stem) or "app"


class ApkDecompile(BaseMobileSkill):
    """Decode an APK with apktool into /loot for downstream analysis."""

    tool = "apktool"
    tool_version_command = "apktool --version 2>&1"

    def analyze(self, **kwargs) -> dict:
        apk = self.resolve_apk(kwargs.get("apk"))
        resources_only = bool(kwargs.get("resources_only", False))
        out_dir = kwargs.get("output_dir") or os.path.join(
            self.loot_path, f"{_safe_stem(apk)}-decompiled"
        )

        flags = "-f"
        if resources_only:
            flags += " -s"  # skip DEX -> smali; manifest + resources only
        result = self.run_tool(f"apktool d {flags} -o {out_dir!r} {apk!r}")

        if "error" in result:
            raise RuntimeError(result["error"])
        if result["exit_code"] != 0 and not os.path.isdir(out_dir):
            self._errors.append(result.get("stderr", "").strip())
            raise RuntimeError(f"apktool decode failed (exit {result['exit_code']})")

        if result.get("stderr", "").strip():
            self._errors.append(result["stderr"].strip())

        file_count = sum(len(files) for _, _, files in os.walk(out_dir))
        self.track_artifact(out_dir)
        return {
            "apk": apk,
            "output_dir": out_dir,
            "resources_only": resources_only,
            "file_count": file_count,
        }


class ManifestScan(BaseMobileSkill):
    """Decode the manifest and flag the usual Android misconfigurations."""

    tool = "apktool"
    tool_version_command = "apktool --version 2>&1"

    def analyze(self, **kwargs) -> dict:
        apk = self.resolve_apk(kwargs.get("apk"))
        out_dir = os.path.join(self.loot_path, f"{_safe_stem(apk)}-manifest")

        # -s: skip smali (we only need the manifest + apktool.yml) -> much faster.
        result = self.run_tool(f"apktool d -s -f -o {out_dir!r} {apk!r}")
        manifest_path = os.path.join(out_dir, "AndroidManifest.xml")
        if not os.path.isfile(manifest_path):
            if "error" in result:
                raise RuntimeError(result["error"])
            raise RuntimeError(
                f"apktool did not produce a manifest (exit {result.get('exit_code')})"
            )
        self.track_artifact(out_dir)

        tree = ET.parse(manifest_path)
        root = tree.getroot()
        package = root.get("package", "")

        app = root.find("application")
        app_flags = {
            "debuggable": _android_attr(app, "debuggable") == "true" if app is not None else False,
            "allow_backup": (
                self._tri(_android_attr(app, "allowBackup")) if app is not None else None
            ),
            "uses_cleartext_traffic": (
                self._tri(_android_attr(app, "usesCleartextTraffic")) if app is not None else None
            ),
            "network_security_config": (
                _android_attr(app, "networkSecurityConfig") if app is not None else None
            ),
        }

        permissions = sorted(
            {
                _android_attr(p, "name")
                for p in root.findall("uses-permission")
                if _android_attr(p, "name")
            }
        )
        custom_permissions = [
            {
                "name": _android_attr(p, "name"),
                "protection_level": _android_attr(p, "protectionLevel") or "normal",
            }
            for p in root.findall("permission")
            if _android_attr(p, "name")
        ]

        exported = {"activities": [], "services": [], "receivers": [], "providers": []}
        tag_to_bucket = {
            "activity": "activities",
            "activity-alias": "activities",
            "service": "services",
            "receiver": "receivers",
            "provider": "providers",
        }
        deeplinks = []
        if app is not None:
            for tag, bucket in tag_to_bucket.items():
                for comp in app.findall(tag):
                    name = _android_attr(comp, "name")
                    if self._is_exported(comp):
                        exported[bucket].append(
                            {
                                "name": name,
                                "permission": _android_attr(comp, "permission"),
                                "has_intent_filter": comp.find("intent-filter") is not None,
                            }
                        )
                    deeplinks.extend(self._extract_deeplinks(comp))

        exported_count = sum(len(v) for v in exported.values())

        risk_notes = self._risk_notes(app_flags, exported, deeplinks)

        # SDK versions live in apktool.yml (apktool relocates uses-sdk there).
        sdk = self._read_sdk(os.path.join(out_dir, "apktool.yml"))

        findings = {
            "package": package,
            "sdk": sdk,
            "application_flags": app_flags,
            "permissions": permissions,
            "permission_count": len(permissions),
            "custom_permissions": custom_permissions,
            "exported_components": exported,
            "exported_component_count": exported_count,
            "deeplinks": sorted(set(deeplinks)),
            "risk_notes": risk_notes,
            "notes": [
                "Exported-component detection is a heuristic: explicit "
                "android:exported wins; otherwise presence of an intent-filter is "
                "treated as exported. Provider defaults vary by targetSdk — verify "
                "flagged providers manually.",
            ],
        }
        self.save_json(f"{_safe_stem(apk)}-manifest-scan.json", findings)
        return findings

    @staticmethod
    def _tri(value):
        """Tri-state: True/False/None (attribute absent)."""
        if value is None:
            return None
        return value.lower() == "true"

    @staticmethod
    def _is_exported(comp) -> bool:
        explicit = _android_attr(comp, "exported")
        if explicit is not None:
            return explicit.lower() == "true"
        return comp.find("intent-filter") is not None

    @staticmethod
    def _extract_deeplinks(comp) -> list[str]:
        links = []
        for ifilter in comp.findall("intent-filter"):
            for data in ifilter.findall("data"):
                scheme = _android_attr(data, "scheme")
                host = _android_attr(data, "host")
                path = (
                    _android_attr(data, "path")
                    or _android_attr(data, "pathPrefix")
                    or _android_attr(data, "pathPattern")
                    or ""
                )
                if scheme:
                    links.append(f"{scheme}://{host or ''}{path}")
        return links

    @staticmethod
    def _risk_notes(app_flags, exported, deeplinks) -> list[str]:
        notes = []
        if app_flags.get("debuggable"):
            notes.append("android:debuggable=true — app is debuggable in production build.")
        if app_flags.get("allow_backup") is True:
            notes.append("android:allowBackup=true — app data can be extracted via adb backup.")
        if app_flags.get("uses_cleartext_traffic") is True:
            notes.append("android:usesCleartextTraffic=true — cleartext HTTP permitted.")
        unprotected = [
            c["name"] for bucket in exported.values() for c in bucket if not c.get("permission")
        ]
        if unprotected:
            notes.append(
                f"{len(unprotected)} exported component(s) without a permission guard: "
                + ", ".join(n for n in unprotected[:10] if n)
            )
        if deeplinks:
            notes.append(
                f"{len(set(deeplinks))} deeplink pattern(s) declared — review for open redirect / injection."
            )
        return notes

    @staticmethod
    def _read_sdk(yml_path) -> dict:
        sdk = {"min": None, "target": None}
        if not os.path.isfile(yml_path):
            return sdk
        try:
            with open(yml_path) as f:
                text = f.read()
        except OSError:
            return sdk
        min_m = re.search(r"minSdkVersion:\s*['\"]?(\d+)", text)
        tgt_m = re.search(r"targetSdkVersion:\s*['\"]?(\d+)", text)
        if min_m:
            sdk["min"] = int(min_m.group(1))
        if tgt_m:
            sdk["target"] = int(tgt_m.group(1))
        return sdk


class SecretScan(BaseMobileSkill):
    """Regex sweep of a decompiled APK tree for hardcoded secrets and endpoints."""

    tool = ""  # pure-Python; decompiles via apktool only when handed a raw APK
    tool_version_command = ""

    # (name, compiled pattern, whether to redact the match in output)
    PATTERNS = [
        ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}"), False),
        ("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{35}"), True),
        ("firebase_db_url", re.compile(r"[a-z0-9.-]+\.firebaseio\.com"), False),
        ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"), True),
        (
            "private_key",
            re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
            False,
        ),
        (
            "jwt",
            re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
            True,
        ),
        (
            "generic_secret_assignment",
            re.compile(
                r"(?i)(?:api[_-]?key|secret|password|passwd|token)\s*[=:]\s*"
                r"['\"][^'\"]{6,}['\"]"
            ),
            True,
        ),
    ]

    SCAN_EXTS = {".smali", ".xml", ".json", ".properties", ".txt", ".js", ".html", ".kt", ".java"}
    MAX_FILE_BYTES = 2_000_000

    def analyze(self, **kwargs) -> dict:
        source_dir = kwargs.get("source_dir")
        if not source_dir:
            apk = self.resolve_apk(kwargs.get("apk"))
            source_dir = os.path.join(self.loot_path, f"{_safe_stem(apk)}-secretscan")
            import shutil  # noqa: PLC0415

            if not shutil.which("apktool"):
                raise RuntimeError(
                    "No source_dir given and apktool is unavailable to decompile the APK."
                )
            result = self.run_tool(f"apktool d -f -o {source_dir!r} {apk!r}")
            if not os.path.isdir(source_dir):
                raise RuntimeError(
                    f"apktool decode failed: {result.get('stderr') or result.get('error')}"
                )
            self.track_artifact(source_dir)
        if not os.path.isdir(source_dir):
            raise FileNotFoundError(f"source_dir not found: {source_dir!r}")

        matches = []
        endpoints = set()
        url_re = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")
        files_scanned = 0

        for dirpath, _, filenames in os.walk(source_dir):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in self.SCAN_EXTS and fname != "AndroidManifest.xml":
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    if os.path.getsize(fpath) > self.MAX_FILE_BYTES:
                        continue
                    with open(fpath, "r", errors="ignore") as f:
                        lines = f.readlines()
                except OSError:
                    continue
                files_scanned += 1
                rel = os.path.relpath(fpath, source_dir)
                for lineno, line in enumerate(lines, 1):
                    for name, pattern, redact in self.PATTERNS:
                        m = pattern.search(line)
                        if m:
                            matches.append(
                                {
                                    "type": name,
                                    "file": rel,
                                    "line": lineno,
                                    "match": self._redact(m.group(0)) if redact else m.group(0),
                                }
                            )
                    for u in url_re.findall(line):
                        endpoints.add(u.rstrip(".,);\"'"))

        findings = {
            "source_dir": source_dir,
            "files_scanned": files_scanned,
            "secret_matches": matches,
            "secret_match_count": len(matches),
            "endpoints": sorted(endpoints)[:200],
            "endpoint_count": len(endpoints),
        }
        stem = _safe_stem(source_dir)
        self.save_json(f"{stem}-secrets.json", findings)
        return findings

    @staticmethod
    def _redact(value: str) -> str:
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}…{value[-4:]}"


class MobileNucleiScan(BaseMobileSkill):
    """Run the mobile nuclei template set over a decompiled APK tree.

    Uses the optiv/mobile-nuclei-templates set baked into the image
    (MOBILE_NUCLEI_TEMPLATES). These are file-protocol templates, so the target
    is a directory of decompiled sources, not a URL, and nuclei must run in file
    mode (`-file`) — without it nuclei aborts with "no templates provided for
    scan". Verified against nuclei v3.11.
    """

    tool = "nuclei"
    tool_version_command = "nuclei -version 2>&1"

    def analyze(self, **kwargs) -> dict:
        source_dir = kwargs.get("source_dir")
        if not source_dir:
            raise ValueError(
                "MobileNucleiScan needs a 'source_dir' (a decompiled tree from ApkDecompile)."
            )
        if not os.path.isdir(source_dir):
            raise FileNotFoundError(f"source_dir not found: {source_dir!r}")

        templates = kwargs.get("templates") or os.environ.get(
            "MOBILE_NUCLEI_TEMPLATES", "/opt/mobile-nuclei-templates"
        )
        extra_args = kwargs.get("extra_args", "")
        out_file = os.path.join(self.loot_path, f"{_safe_stem(source_dir)}-nuclei.jsonl")

        # -file is mandatory for file-protocol templates over a source tree.
        cmd = (
            f"nuclei -disable-update-check -no-color -silent -file "
            f"-jsonl -o {out_file!r} -target {source_dir!r} -t {templates!r} {extra_args}".strip()
        )
        result = self.run_tool(cmd)
        if "error" in result:
            raise RuntimeError(result["error"])
        # A fatal nuclei error (bad flags, unreadable templates) exits non-zero
        # and writes no output. Don't mask that as a clean "0 results" scan.
        if result.get("exit_code", 0) != 0 and not os.path.isfile(out_file):
            detail = (result.get("stderr") or result.get("stdout") or "").strip()
            raise RuntimeError(f"nuclei exited {result['exit_code']}: {detail[-500:]}")
        if result.get("stderr", "").strip():
            self._errors.append(result["stderr"].strip())

        results = []
        if os.path.isfile(out_file):
            self.track_artifact(out_file)
            with open(out_file, "r", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    info = obj.get("info", {})
                    results.append(
                        {
                            "template_id": obj.get("template-id") or obj.get("templateID"),
                            "name": info.get("name"),
                            "severity": info.get("severity"),
                            "matched": obj.get("matched-at") or obj.get("matched"),
                        }
                    )

        return {
            "source_dir": source_dir,
            "templates": templates,
            "result_count": len(results),
            "results": results,
        }

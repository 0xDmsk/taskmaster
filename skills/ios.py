"""
iOS static-analysis skills (Phase 1 — no device/Mac required).

Scope is deliberately narrower than the Android side (`skills/mobile.py`):
there is no jadx equivalent here. Android release APKs decompile to
near-source Java even unobfuscated; a release IPA's Mach-O binary is stripped
ARM64, and headless disassembly (e.g. Ghidra) yields low-fidelity pseudo-C
with no recovered class/method names — not a useful code-review artifact. So
this module intentionally stops at bundle-level static review: Info.plist,
entitlements, and the same regex secret sweep used for Android, run over the
unpacked `.app`. It does not attempt binary decompilation or run
`MobileNucleiScan` (the optiv template set is Android-skewed).

Everything runs headless with tools already in the mobile image (`openssl`
for CMS-signed provisioning-profile decoding; `zipfile`/`plistlib` are Python
stdlib — an IPA is a zip and both binary and XML plists parse natively).

Skills:
  * IpaUnpack     — unzip an IPA and locate its Payload/*.app bundle
  * InfoPlistScan — parse Info.plist + embedded.mobileprovision entitlements
                    for the usual iOS misconfigurations

`mobile.SecretScan` is reused unchanged for the secret sweep — point its
`source_dir` at the unpacked `.app` bundle (`IpaUnpack`'s `app_dir`).
"""

import os
import plistlib
import subprocess
import zipfile

from skills.mobile_base import BaseMobileSkill, _safe_stem


def _find_app_bundle(root: str) -> str:
    """Return the single *.app bundle under `root` or `root/Payload`."""
    for base in (os.path.join(root, "Payload"), root):
        if not os.path.isdir(base):
            continue
        apps = sorted(
            d
            for d in os.listdir(base)
            if d.endswith(".app") and os.path.isdir(os.path.join(base, d))
        )
        if len(apps) == 1:
            return os.path.join(base, apps[0])
        if len(apps) > 1:
            raise RuntimeError(f"Multiple .app bundles found under {base!r}: {apps}")
    raise RuntimeError(f"No .app bundle found under {root!r} (expected Payload/*.app).")


def _resolve_app_dir(skill: BaseMobileSkill, kwargs: dict) -> str:
    """Resolve an unpacked .app bundle: `app_dir` wins, then `source_dir`
    (an `IpaUnpack` output_dir — Payload/*.app is located inside it), then
    `ipa`/auto-discovery (unpacked fresh into /loot)."""
    app_dir = kwargs.get("app_dir")
    if app_dir:
        if not os.path.isdir(app_dir):
            raise FileNotFoundError(f"app_dir not found: {app_dir!r}")
        return app_dir

    source_dir = kwargs.get("source_dir")
    if source_dir:
        if not os.path.isdir(source_dir):
            raise FileNotFoundError(f"source_dir not found: {source_dir!r}")
        return _find_app_bundle(source_dir)

    ipa = skill.resolve_ipa(kwargs.get("ipa"))
    out_dir = os.path.join(skill.loot_path, f"{_safe_stem(ipa)}-unpacked")
    with zipfile.ZipFile(ipa) as zf:
        zf.extractall(out_dir)
    skill.track_artifact(out_dir)
    return _find_app_bundle(out_dir)


class IpaUnpack(BaseMobileSkill):
    """Unzip an IPA and locate its .app bundle — the iOS equivalent of the
    file-layout half of `ApkDecompile` (there is no decoding step: the
    payload is already resources plus a compiled binary)."""

    tool = ""
    tool_version_command = ""

    def analyze(self, **kwargs) -> dict:
        ipa = self.resolve_ipa(kwargs.get("ipa"))
        out_dir = kwargs.get("output_dir") or os.path.join(
            self.loot_path, f"{_safe_stem(ipa)}-unpacked"
        )
        with zipfile.ZipFile(ipa) as zf:
            zf.extractall(out_dir)
        app_dir = _find_app_bundle(out_dir)
        self.track_artifact(out_dir)

        file_count = sum(len(files) for _, _, files in os.walk(out_dir))
        return {
            "ipa": ipa,
            "output_dir": out_dir,
            "app_dir": app_dir,
            "file_count": file_count,
        }


class InfoPlistScan(BaseMobileSkill):
    """Parse Info.plist (and embedded.mobileprovision, if present) for the
    usual iOS misconfigurations. Accepts `app_dir` (an unpacked .app bundle),
    `source_dir` (an `IpaUnpack` output_dir), or `ipa` (unpacked fresh)."""

    tool = "openssl"
    tool_version_command = "openssl version"

    def analyze(self, **kwargs) -> dict:
        app_dir = _resolve_app_dir(self, kwargs)
        plist_path = os.path.join(app_dir, "Info.plist")
        if not os.path.isfile(plist_path):
            raise FileNotFoundError(f"Info.plist not found in {app_dir!r}")
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f)

        bundle_id = plist.get("CFBundleIdentifier")
        version = {
            "short": plist.get("CFBundleShortVersionString"),
            "build": plist.get("CFBundleVersion"),
        }

        ats = plist.get("NSAppTransportSecurity") or {}
        ats_flags = {
            "arbitrary_loads": bool(ats.get("NSAllowsArbitraryLoads")),
            "arbitrary_loads_in_web_content": bool(ats.get("NSAllowsArbitraryLoadsInWebContent")),
            "exception_domains": sorted((ats.get("NSExceptionDomains") or {}).keys()),
        }

        url_schemes = []
        for entry in plist.get("CFBundleURLTypes") or []:
            url_schemes.extend(entry.get("CFBundleURLSchemes") or [])

        file_sharing = bool(plist.get("UIFileSharingEnabled"))
        background_modes = sorted(set(plist.get("UIBackgroundModes") or []))
        queries_schemes = sorted(set(plist.get("LSApplicationQueriesSchemes") or []))

        entitlements, provisioning_note = self._read_entitlements(app_dir)
        risk_notes = self._risk_notes(ats_flags, file_sharing, url_schemes, entitlements)

        notes = [
            "Static Info.plist/entitlements review only — no binary or code "
            "analysis. See skills/ios.py module docstring for why this worker "
            "has no ApkDecompile/jadx equivalent for iOS.",
        ]
        if provisioning_note:
            notes.append(provisioning_note)

        findings = {
            "bundle_id": bundle_id,
            "version": version,
            "minimum_os_version": plist.get("MinimumOSVersion"),
            "ats": ats_flags,
            "url_schemes": sorted(set(url_schemes)),
            "queries_schemes": queries_schemes,
            "file_sharing_enabled": file_sharing,
            "background_modes": background_modes,
            "uses_non_exempt_encryption": plist.get("ITSAppUsesNonExemptEncryption"),
            "entitlements": entitlements,
            "risk_notes": risk_notes,
            "notes": notes,
        }
        self.save_json(f"{_safe_stem(app_dir)}-infoplist-scan.json", findings)
        return findings

    @staticmethod
    def _read_entitlements(app_dir: str) -> tuple[dict, str | None]:
        """Best-effort entitlements via embedded.mobileprovision (a CMS-signed
        plist). Returns (entitlements, note). Absent on IPAs pulled without a
        provisioning profile — that's normal, not an error."""
        provision_path = os.path.join(app_dir, "embedded.mobileprovision")
        if not os.path.isfile(provision_path):
            return {}, None
        try:
            result = subprocess.run(
                [
                    "openssl",
                    "smime",
                    "-verify",
                    "-noverify",
                    "-inform",
                    "DER",
                    "-in",
                    provision_path,
                ],
                capture_output=True,
                timeout=30,
            )
        except Exception as e:
            return {}, f"embedded.mobileprovision present but openssl failed: {e}"
        if result.returncode != 0 or not result.stdout:
            return (
                {},
                "embedded.mobileprovision present but could not be decoded (openssl smime failed).",
            )
        try:
            profile = plistlib.loads(result.stdout)
        except Exception:
            return {}, "embedded.mobileprovision decoded but was not a valid plist."
        return profile.get("Entitlements") or {}, None

    @staticmethod
    def _risk_notes(ats_flags, file_sharing, url_schemes, entitlements) -> list[str]:
        notes = []
        if ats_flags["arbitrary_loads"]:
            notes.append(
                "NSAllowsArbitraryLoads=true — ATS disabled app-wide, cleartext/weak-TLS HTTP permitted."
            )
        if ats_flags["arbitrary_loads_in_web_content"]:
            notes.append(
                "NSAllowsArbitraryLoadsInWebContent=true — ATS disabled for WKWebView/UIWebView content."
            )
        if ats_flags["exception_domains"]:
            notes.append(
                f"{len(ats_flags['exception_domains'])} ATS exception domain(s): "
                + ", ".join(ats_flags["exception_domains"][:10])
            )
        if file_sharing:
            notes.append(
                "UIFileSharingEnabled=true — app's Documents directory exposed via Finder/iTunes file sharing."
            )
        if url_schemes:
            notes.append(
                f"{len(set(url_schemes))} custom URL scheme(s) registered — review handlers for "
                "open-redirect/injection: " + ", ".join(sorted(set(url_schemes))[:10])
            )
        if entitlements.get("get-task-allow") is True:
            notes.append(
                "get-task-allow=true in entitlements — debuggable/attachable build (should not ship to production)."
            )
        return notes

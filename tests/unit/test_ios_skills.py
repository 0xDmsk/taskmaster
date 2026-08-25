import os
import plistlib
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import skills.ios as ios
import skills.mobile as mobile

INFO_PLIST = {
    "CFBundleIdentifier": "com.example.vuln",
    "CFBundleShortVersionString": "1.2.3",
    "CFBundleVersion": "42",
    "MinimumOSVersion": "15.0",
    "NSAppTransportSecurity": {
        "NSAllowsArbitraryLoads": True,
        "NSExceptionDomains": {"example.com": {}},
    },
    "CFBundleURLTypes": [{"CFBundleURLSchemes": ["myapp"]}],
    "LSApplicationQueriesSchemes": ["fb", "twitter"],
    "UIFileSharingEnabled": True,
    "UIBackgroundModes": ["fetch"],
}


def _write_ipa(path, bundle_id="com.example.vuln", extra_files=None):
    app_dir = f"Payload/{bundle_id}.app"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{app_dir}/Info.plist", plistlib.dumps(INFO_PLIST))
        for name, content in (extra_files or {}).items():
            zf.writestr(f"{app_dir}/{name}", content)


def test_ipa_unpack_locates_app_bundle(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    ipa = loot / "app.ipa"
    _write_ipa(str(ipa))

    skill = ios.IpaUnpack(target=None)
    skill.loot_path = str(loot)
    env = skill.run(ipa=str(ipa))

    assert env["status"] == "success", env["errors"]
    f = env["findings"]
    assert f["app_dir"].endswith("com.example.vuln.app")
    assert os.path.isdir(f["app_dir"])
    assert f["file_count"] >= 1


def test_ipa_unpack_multiple_app_bundles_is_an_error(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    ipa = loot / "app.ipa"
    with zipfile.ZipFile(ipa, "w") as zf:
        zf.writestr("Payload/One.app/Info.plist", plistlib.dumps(INFO_PLIST))
        zf.writestr("Payload/Two.app/Info.plist", plistlib.dumps(INFO_PLIST))

    skill = ios.IpaUnpack(target=None)
    skill.loot_path = str(loot)
    env = skill.run(ipa=str(ipa))

    assert env["status"] == "error"
    assert any("Multiple .app bundles" in e for e in env["errors"])


def test_infoplist_scan_flags_misconfigurations_from_ipa(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    ipa = loot / "app.ipa"
    _write_ipa(str(ipa))

    skill = ios.InfoPlistScan(target=None)
    skill.loot_path = str(loot)
    env = skill.run(ipa=str(ipa))

    assert env["status"] == "success", env["errors"]
    f = env["findings"]
    assert f["bundle_id"] == "com.example.vuln"
    assert f["version"] == {"short": "1.2.3", "build": "42"}
    assert f["ats"]["arbitrary_loads"] is True
    assert f["ats"]["exception_domains"] == ["example.com"]
    assert f["url_schemes"] == ["myapp"]
    assert f["file_sharing_enabled"] is True
    assert f["entitlements"] == {}
    assert any("NSAllowsArbitraryLoads" in n for n in f["risk_notes"])
    assert any("UIFileSharingEnabled" in n for n in f["risk_notes"])


def test_infoplist_scan_reuses_source_dir_from_ipa_unpack(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    ipa = loot / "app.ipa"
    _write_ipa(str(ipa))

    unpack = ios.IpaUnpack(target=None)
    unpack.loot_path = str(loot)
    unpack_env = unpack.run(ipa=str(ipa))
    assert unpack_env["status"] == "success"

    scan = ios.InfoPlistScan(target=None)
    scan.loot_path = str(loot)
    env = scan.run(source_dir=unpack_env["findings"]["output_dir"])

    assert env["status"] == "success", env["errors"]
    assert env["findings"]["bundle_id"] == "com.example.vuln"


def test_infoplist_scan_missing_info_plist_is_clean_error(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    app_dir = loot / "empty.app"
    app_dir.mkdir()

    skill = ios.InfoPlistScan(target=None)
    skill.loot_path = str(loot)
    env = skill.run(app_dir=str(app_dir))

    assert env["status"] == "error"
    assert any("Info.plist not found" in e for e in env["errors"])
    assert not any("Traceback" in e for e in env["errors"])


def test_secret_scan_reused_against_unpacked_ios_bundle(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    ipa = loot / "app.ipa"
    _write_ipa(
        str(ipa),
        extra_files={"Secrets.strings": '"api_key" = "AKIAABCDEFGHIJKLMNOP";'},
    )

    unpack = ios.IpaUnpack(target=None)
    unpack.loot_path = str(loot)
    unpack_env = unpack.run(ipa=str(ipa))

    skill = mobile.SecretScan(target=None)
    skill.loot_path = str(loot)
    env = skill.run(source_dir=unpack_env["findings"]["output_dir"])

    assert env["status"] == "success", env["errors"]
    matches = env["findings"]["secret_matches"]
    assert any(m["type"] == "aws_access_key" for m in matches)


def test_resolve_ipa_auto_discovers_single_ipa(tmp_path, monkeypatch):
    monkeypatch.setenv("SESSION_DIR", str(tmp_path / "no-session"))
    loot = tmp_path / "loot"
    loot.mkdir()
    ipa = loot / "app.ipa"
    ipa.write_bytes(b"")

    skill = ios.InfoPlistScan(target="com.example.app")
    skill.loot_path = str(loot)
    assert skill.resolve_ipa(None) == str(ipa)


def test_resolve_ipa_ambiguous_when_multiple(tmp_path, monkeypatch):
    monkeypatch.setenv("SESSION_DIR", str(tmp_path / "no-session"))
    loot = tmp_path / "loot"
    loot.mkdir()
    (loot / "a.ipa").write_bytes(b"")
    (loot / "b.ipa").write_bytes(b"")

    skill = ios.InfoPlistScan(target=None)
    skill.loot_path = str(loot)
    with pytest.raises(ValueError, match="Multiple IPAs"):
        skill.resolve_ipa(None)

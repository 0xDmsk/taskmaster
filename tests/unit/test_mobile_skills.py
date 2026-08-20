import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import skills.mobile as mobile

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.example.vuln">
  <uses-permission android:name="android.permission.INTERNET"/>
  <uses-permission android:name="android.permission.READ_SMS"/>
  <permission android:name="com.example.vuln.CUSTOM" android:protectionLevel="normal"/>
  <application android:debuggable="true" android:allowBackup="true" android:usesCleartextTraffic="true">
    <activity android:name=".MainActivity">
      <intent-filter><action android:name="android.intent.action.MAIN"/></intent-filter>
    </activity>
    <activity android:name=".DeepLinkActivity" android:exported="true">
      <intent-filter android:autoVerify="true">
        <data android:scheme="myapp" android:host="open" android:pathPrefix="/pay"/>
      </intent-filter>
    </activity>
    <service android:name=".SecretService" android:exported="true"/>
    <provider android:name=".DataProvider" android:exported="true" android:permission="com.example.vuln.CUSTOM"/>
    <receiver android:name=".InternalReceiver" android:exported="false"/>
  </application>
</manifest>"""


def _fake_decompiled_manifest(loot_dir):
    """Lay out a manifest dir the way apktool would, under <loot>/app-manifest."""
    out_dir = os.path.join(loot_dir, "app-manifest")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "AndroidManifest.xml"), "w") as f:
        f.write(MANIFEST)
    with open(os.path.join(out_dir, "apktool.yml"), "w") as f:
        f.write("sdkInfo:\n  minSdkVersion: '21'\n  targetSdkVersion: '33'\n")


def test_manifest_scan_flags_misconfigurations(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    _fake_decompiled_manifest(str(loot))
    apk = loot / "app.apk"
    apk.write_bytes(b"")

    skill = mobile.ManifestScan(target=None)
    skill.loot_path = str(loot)
    # apktool is not installed on the test host; stub the decode + version probe.
    skill.run_tool = lambda *a, **k: {"stdout": "", "stderr": "", "exit_code": 0}
    skill._ensure_tool_available = lambda: None
    skill._detect_tool_version = lambda: "apktool (stub)"

    env = skill.run(apk=str(apk))
    assert env["status"] == "success", env["errors"]
    f = env["findings"]

    assert f["package"] == "com.example.vuln"
    assert f["sdk"] == {"min": 21, "target": 33}
    assert f["application_flags"]["debuggable"] is True
    assert f["application_flags"]["allow_backup"] is True
    assert f["application_flags"]["uses_cleartext_traffic"] is True

    # MainActivity (intent-filter, no explicit exported), DeepLinkActivity,
    # SecretService, DataProvider are exported; InternalReceiver is not.
    assert f["exported_component_count"] == 4
    exported_names = {c["name"] for bucket in f["exported_components"].values() for c in bucket}
    assert ".InternalReceiver" not in exported_names
    assert ".DataProvider" in exported_names

    # The permission-guarded provider must not appear in the "unprotected" note.
    unprotected_note = next(n for n in f["risk_notes"] if "without a permission guard" in n)
    assert ".DataProvider" not in unprotected_note
    assert ".SecretService" in unprotected_note

    assert "myapp://open/pay" in f["deeplinks"]


def test_secret_scan_finds_and_redacts(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    src = tmp_path / "decompiled" / "smali"
    src.mkdir(parents=True)
    (src / "Config.smali").write_text(
        'const-string v0, "AKIAIOSFODNN7EXAMPLE"\n'
        'const-string v1, "https://api.example.com/v1/login"\n'
        'const-string v2, "AIzaSyA1234567890abcdefghijklmnopqrstuvw"\n'
        'password = "supersecret123"\n'
        'const-string v3, "https://myproj.firebaseio.com"\n'
    )

    skill = mobile.SecretScan(target=None)
    skill.loot_path = str(loot)
    env = skill.run(source_dir=str(tmp_path / "decompiled"))

    assert env["status"] == "success", env["errors"]
    f = env["findings"]
    types = {m["type"] for m in f["secret_matches"]}
    assert {"aws_access_key", "google_api_key", "firebase_db_url"} <= types

    # AWS keys are not redacted (the prefix is not sensitive); Google keys are.
    aws = next(m for m in f["secret_matches"] if m["type"] == "aws_access_key")
    assert aws["match"] == "AKIAIOSFODNN7EXAMPLE"
    google = next(m for m in f["secret_matches"] if m["type"] == "google_api_key")
    assert "…" in google["match"]

    assert "https://api.example.com/v1/login" in f["endpoints"]


def test_nuclei_scan_accepts_source_dir(tmp_path):
    # Uniform contract: MobileNucleiScan takes source_dir (like SecretScan),
    # not only apk. This is the interface-consistency regression.
    loot = tmp_path / "loot"
    loot.mkdir()
    src = tmp_path / "decompiled"
    src.mkdir()

    skill = mobile.MobileNucleiScan(target=None)
    skill.loot_path = str(loot)
    skill._ensure_tool_available = lambda: None  # nuclei not required on test host
    skill._detect_tool_version = lambda: "nuclei (stub)"
    # Stub the scan itself; we're testing argument handling, not nuclei.
    skill.run_tool = lambda *a, **k: {"stdout": "", "stderr": "", "exit_code": 0}

    env = skill.run(source_dir=str(src))
    assert env["status"] == "success", env["errors"]
    assert env["findings"]["source_dir"] == str(src)


def test_nuclei_scan_returns_partial_results_on_timeout(tmp_path):
    # A long scan that hits the wall-clock should return whatever nuclei already
    # streamed to the JSONL file, not fail or discard everything.
    loot = tmp_path / "loot"
    loot.mkdir()
    src = tmp_path / "decompiled"
    src.mkdir()
    out_file = loot / f"{src.name}-nuclei.jsonl"
    out_file.write_text(
        '{"template-id": "android-debug-enabled", "info": {"name": "Debug", '
        '"severity": "low"}, "matched-at": "AndroidManifest.xml"}\n'
    )

    skill = mobile.MobileNucleiScan(target=None)
    skill.loot_path = str(loot)
    skill._ensure_tool_available = lambda: None
    skill._detect_tool_version = lambda: "nuclei (stub)"
    # Simulate a run that timed out after writing one partial result.
    skill.run_tool = lambda *a, **k: {"error": "Command timed out after 8s", "timed_out": True}

    env = skill.run(source_dir=str(src), timeout=8)
    assert env["status"] == "success", env["errors"]
    assert env["findings"]["timed_out"] is True
    assert env["findings"]["result_count"] == 1
    assert any("wall-clock" in e for e in env["errors"])


def _fake_decompiled_app(root, package="com.example.app", with_first_party=True):
    """A minimal decompiled tree: manifest + first-party + third-party smali."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "AndroidManifest.xml").write_text(
        '<?xml version="1.0"?>\n'
        f'<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{package}">'
        "<application/></manifest>"
    )
    # Third-party smali always present (the bulk on a real app).
    (root / "smali" / "androidx" / "core").mkdir(parents=True)
    (root / "smali" / "kotlin").mkdir(parents=True)
    # res/xml is security-relevant config; the rest of res/ is bulky non-code.
    (root / "res" / "xml").mkdir(parents=True)
    (root / "res" / "xml" / "network_security_config.xml").write_text("<network-security-config/>")
    (root / "res" / "drawable").mkdir(parents=True)
    (root / "res" / "drawable" / "icon.xml").write_text("<vector/>")
    if with_first_party:
        seg = os.path.join(*package.split(".")[:2])
        (root / "smali" / seg).mkdir(parents=True)
        (root / "smali_classes2" / seg).mkdir(parents=True)


def test_nuclei_first_party_scopes_to_app_package(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    src = tmp_path / "decompiled"
    _fake_decompiled_app(src)

    skill = mobile.MobileNucleiScan(target=None)
    skill.loot_path = str(loot)
    flag, note = skill._resolve_targets(str(src), {"first_party": True})

    # Uses a -l list file, not a full -target of the whole tree.
    assert flag.startswith("-l ")
    assert "com/example" in note
    scope_path = next(a for a in skill._artifacts if a.endswith("nuclei-scope.txt"))
    scoped = open(scope_path).read()
    # First-party smali from both roots is included; third-party is not.
    assert "smali/com/example" in scoped
    assert "smali_classes2/com/example" in scoped
    assert "androidx" not in scoped
    assert "kotlin" not in scoped
    # res/xml (config) is in scope; the bulky rest of res/ is not.
    assert "res/xml" in scoped
    assert "res/drawable" not in scoped


def test_nuclei_first_party_falls_back_when_no_app_smali(tmp_path):
    loot = tmp_path / "loot"
    loot.mkdir()
    src = tmp_path / "decompiled"
    _fake_decompiled_app(src, package="com.example.app", with_first_party=False)

    skill = mobile.MobileNucleiScan(target=None)
    skill.loot_path = str(loot)
    flag, note = skill._resolve_targets(str(src), {"first_party": True})

    # No first-party smali -> scan the whole tree, with an explanatory note.
    assert flag == f"-target {str(src)!r}"
    assert "scanned full tree" in note


def test_nuclei_default_scans_whole_tree(tmp_path):
    src = tmp_path / "decompiled"
    _fake_decompiled_app(src)
    skill = mobile.MobileNucleiScan(target=None)
    skill.loot_path = str(tmp_path)
    flag, note = skill._resolve_targets(str(src), {})
    assert flag == f"-target {str(src)!r}"
    assert note is None


def test_nuclei_scan_missing_input_is_clean_error(tmp_path):
    skill = mobile.MobileNucleiScan(target=None)
    skill.loot_path = str(tmp_path)
    skill._ensure_tool_available = lambda: None
    skill._detect_tool_version = lambda: ""

    env = skill.run()  # neither source_dir nor apk
    assert env["status"] == "error"
    assert any("apk" in e.lower() for e in env["errors"])
    # A missing-argument error must be a clean message, not a stack trace.
    assert not any("Traceback" in e for e in env["errors"])


def test_manifest_scan_requires_apk(tmp_path):
    skill = mobile.ManifestScan(target=None)
    skill.loot_path = str(tmp_path)
    skill._ensure_tool_available = lambda: None
    skill._detect_tool_version = lambda: ""

    env = skill.run()  # no apk / target
    assert env["status"] == "error"
    assert any("apk" in e.lower() for e in env["errors"])

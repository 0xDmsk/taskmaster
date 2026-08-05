"""
Unit tests for each skill's build_command() and parse_output().
"""

import json
import os
import sys

import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from skills.network import FpingSweep, NmapScan
from skills.web import FfufFuzz, HttpxDetect
from skills.subdomain import GobusterDns, SubfinderEnum
from skills.takeover import NucleiTakeover
from skills.cloud import (
    AwsCliAudit,
    GcloudAudit,
    IamPrivescFinder,
    _action_matches,
    _flatten_actions,
)
from skills.base import BaseSkill

# --- Network Skills ---


class TestFpingSweep:
    def test_build_command(self):
        skill = FpingSweep(target="192.168.1.0/24")
        cmd = skill.build_command()
        assert "fping -g 192.168.1.0/24 -a" in cmd

    def test_build_command_with_network_kwarg(self):
        skill = FpingSweep()
        cmd = skill.build_command(network="10.0.0.0/24")
        assert "10.0.0.0/24" in cmd

    def test_build_command_no_target(self):
        skill = FpingSweep()
        with pytest.raises(ValueError):
            skill.build_command()

    def test_parse_output(self, tmp_path):
        skill = FpingSweep(target="192.168.1.0/24")
        skill.loot_path = str(tmp_path)
        skill._artifacts = []

        stdout = "192.168.1.1\n192.168.1.5\n192.168.1.10\n"
        result = skill.parse_output(stdout, "", 0)

        assert result["alive_count"] == 3
        assert "192.168.1.1" in result["hosts"]
        assert len(skill._artifacts) == 1


class TestNmapScan:
    def test_build_command_default(self):
        skill = NmapScan(target="10.0.0.1")
        cmd = skill.build_command()
        assert "nmap -sT -sV -T4 10.0.0.1" in cmd
        assert "-oX" in cmd

    def test_build_command_with_ports(self):
        skill = NmapScan(target="10.0.0.1")
        cmd = skill.build_command(ports="80,443")
        assert "-p 80,443" in cmd

    def test_build_command_custom_flags(self):
        skill = NmapScan(target="10.0.0.1")
        cmd = skill.build_command(flags="-sT -A")
        assert "-sT -A" in cmd

    def test_build_command_no_target(self):
        skill = NmapScan()
        with pytest.raises(ValueError):
            skill.build_command()

    def test_parse_nmap_xml(self, tmp_path):
        xml_content = """<?xml version="1.0"?>
        <nmaprun>
          <host>
            <status state="up"/>
            <address addr="10.0.0.1"/>
            <ports>
              <port protocol="tcp" portid="80">
                <state state="open"/>
                <service name="http" product="Apache" version="2.4.52"/>
              </port>
              <port protocol="tcp" portid="22">
                <state state="open"/>
                <service name="ssh" product="OpenSSH" version="8.9"/>
              </port>
            </ports>
          </host>
          <host>
            <status state="down"/>
            <address addr="10.0.0.2"/>
          </host>
        </nmaprun>"""

        xml_path = str(tmp_path / "scan.xml")
        with open(xml_path, "w") as f:
            f.write(xml_content)

        hosts = NmapScan._parse_nmap_xml(xml_path)
        assert len(hosts) == 1
        assert hosts[0]["ip"] == "10.0.0.1"
        assert len(hosts[0]["ports"]) == 2
        assert hosts[0]["ports"][0]["id"] == 80
        assert hosts[0]["ports"][0]["service"] == "http"
        assert hosts[0]["ports"][0]["product"] == "Apache"


# --- Web Skills ---


class TestFfufFuzz:
    def test_build_command_default(self):
        skill = FfufFuzz(target="http://example.com")
        cmd = skill.build_command()
        assert "ffuf -u http://example.com/FUZZ" in cmd
        assert "-mc 200,301,302,403" in cmd
        assert "-of json" in cmd

    def test_build_command_auto_http(self):
        skill = FfufFuzz(target="example.com")
        cmd = skill.build_command()
        assert "http://example.com/FUZZ" in cmd

    def test_build_command_custom_wordlist(self):
        skill = FfufFuzz(target="http://example.com")
        cmd = skill.build_command(wordlist="/tmp/words.txt")
        assert "-w /tmp/words.txt" in cmd

    def test_parse_output_with_results(self, tmp_path):
        skill = FfufFuzz(target="http://example.com")
        skill._artifacts = []
        skill._errors = []
        output_file = str(tmp_path / "ffuf.json")
        skill._output_file = output_file

        ffuf_data = {
            "results": [
                {"url": "http://example.com/admin", "status": 200, "length": 1234},
                {"url": "http://example.com/login", "status": 302, "length": 0},
            ]
        }
        with open(output_file, "w") as f:
            json.dump(ffuf_data, f)

        result = skill.parse_output("", "", 0)
        assert result["directories_found"] == 2
        assert result["directories"][0]["url"] == "http://example.com/admin"

    def test_parse_output_no_file(self, tmp_path):
        skill = FfufFuzz(target="http://example.com")
        skill._artifacts = []
        skill._errors = []
        skill._output_file = str(tmp_path / "nonexistent.json")

        result = skill.parse_output("", "", 0)
        assert result["directories_found"] == 0


class TestHttpxDetect:
    def test_build_command(self):
        skill = HttpxDetect(target="http://example.com")
        cmd = skill.build_command()
        assert "httpx -u http://example.com" in cmd
        assert "-tech-detect" in cmd
        assert "-json" in cmd

    def test_version_command_uses_last_line(self):
        skill = HttpxDetect(target="http://example.com")
        assert skill.tool_version_command == "httpx -version | tail -n 1 2>&1"

    def test_parse_output_with_results(self, tmp_path):
        skill = HttpxDetect(target="http://example.com")
        skill._artifacts = []
        skill._errors = []
        output_file = str(tmp_path / "httpx.json")
        skill._output_file = output_file

        httpx_data = {
            "url": "http://example.com",
            "status_code": 200,
            "title": "Example",
            "webserver": "nginx",
            "tech": ["jQuery", "Bootstrap"],
        }
        with open(output_file, "w") as f:
            f.write(json.dumps(httpx_data) + "\n")

        result = skill.parse_output("", "", 0)
        assert result["url"] == "http://example.com"
        assert result["server"] == "nginx"
        assert "jQuery" in result["technologies"]


class MissingToolSkill(BaseSkill):
    tool = "missing-tool"

    def build_command(self, **kwargs) -> str:
        return "missing-tool --version"

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        return {}


class TestBaseSkillToolAvailability:
    def test_run_fails_fast_when_tool_is_missing(self):
        skill = MissingToolSkill(target="example.com")
        with patch("skills.base.shutil.which", return_value=None):
            result = skill.run()

        assert result["status"] == "error"
        assert "not installed" in result["errors"][0]


# --- Subdomain Skills ---


class TestGobusterDns:
    def test_build_command(self):
        skill = GobusterDns(target="example.com")
        cmd = skill.build_command()
        assert "gobuster dns --domain example.com" in cmd
        assert "-q" in cmd

    def test_build_command_custom_wordlist(self):
        skill = GobusterDns(target="example.com")
        cmd = skill.build_command(wordlist="/tmp/dns.txt")
        assert "-w /tmp/dns.txt" in cmd

    def test_parse_output(self, tmp_path):
        skill = GobusterDns(target="example.com")
        skill.loot_path = str(tmp_path)
        skill._artifacts = []
        skill._domain = "example.com"

        stdout = "Found: api.example.com\nFound: www.example.com\n"
        result = skill.parse_output(stdout, "", 0)
        assert result["subdomains_found"] == 2
        assert "api.example.com" in result["subdomains"]


class TestSubfinderEnum:
    def test_build_command(self):
        skill = SubfinderEnum(target="example.com")
        cmd = skill.build_command()
        assert "subfinder -d example.com" in cmd
        assert "-silent" in cmd

    def test_parse_output_stdout_fallback(self, tmp_path):
        skill = SubfinderEnum(target="example.com")
        skill._artifacts = []
        skill._errors = []
        skill._domain = "example.com"
        skill._output_file = str(tmp_path / "nonexistent.json")

        stdout = "api.example.com\nwww.example.com\n"
        result = skill.parse_output(stdout, "", 0)
        assert result["subdomains_found"] == 2


# --- Takeover Skills ---


class TestNucleiTakeover:
    def test_build_command_with_target(self):
        skill = NucleiTakeover(target="sub.example.com")
        cmd = skill.build_command()
        assert "nuclei -u sub.example.com" in cmd
        assert "http/takeovers/" in cmd

    def test_build_command_with_targets_list(self, tmp_path):
        skill = NucleiTakeover()
        skill.loot_path = str(tmp_path)
        skill._artifacts = []
        cmd = skill.build_command(targets=["a.example.com", "b.example.com"])
        assert "-l" in cmd

    def test_build_command_no_target(self):
        skill = NucleiTakeover()
        with pytest.raises(ValueError):
            skill.build_command()

    def test_parse_output(self, tmp_path):
        skill = NucleiTakeover(target="example.com")
        skill._artifacts = []
        skill._errors = []
        output_file = str(tmp_path / "nuclei_takeover.json")
        skill._output_file = output_file

        nuclei_line = json.dumps(
            {
                "host": "sub.example.com",
                "template-id": "github-takeover",
                "info": {"name": "GitHub Takeover", "severity": "high"},
                "matched-at": "http://sub.example.com",
            }
        )
        with open(output_file, "w") as f:
            f.write(nuclei_line + "\n")

        result = skill.parse_output("", "", 0)
        assert result["vulnerable_count"] == 1
        assert result["vulnerable"][0]["template_id"] == "github-takeover"


# --- Cloud Skills ---


class TestAwsCliAudit:
    def test_build_command_default(self):
        skill = AwsCliAudit(target="aws-account")
        cmd = skill.build_command()
        assert "aws sts get-caller-identity" in cmd
        assert "aws s3api list-buckets" in cmd
        assert "aws iam list-users" in cmd
        assert "---SECTION---" in cmd

    def test_build_command_with_profile(self):
        skill = AwsCliAudit(target="aws-account")
        cmd = skill.build_command(profile="prod")
        assert "--profile prod" in cmd

    def test_build_command_includes_secrets_and_dynamodb(self):
        skill = AwsCliAudit(target="aws-account")
        cmd = skill.build_command()
        assert "aws secretsmanager list-secrets" in cmd
        assert "aws dynamodb list-tables" in cmd

    def test_parse_output(self, tmp_path):
        skill = AwsCliAudit(target="aws-account")
        skill.loot_path = str(tmp_path)
        skill._artifacts = []
        skill._errors = []

        identity = json.dumps({"Account": "123456", "Arn": "arn:aws:iam::root"})
        buckets = json.dumps({"Buckets": [{"Name": "my-bucket"}]})
        users = json.dumps({"Users": [{"UserName": "admin"}]})
        secrets = json.dumps({"SecretList": [{"Name": "db-creds"}]})
        tables = json.dumps({"TableNames": ["Users"]})

        stdout = "\n---SECTION---\n".join([identity, buckets, users, secrets, tables])
        # Flag an interesting key; keep the bucket scan hermetic (no real aws call).
        listing = "2025-01-01 00:00:00  573 webadmin/id_rsa\n2025-01-01 00:00:00 120 css/app.css\n"
        with patch.object(skill, "execute_shell", return_value={"stdout": listing}):
            result = skill.parse_output(stdout, "", 0)

        assert result["buckets_count"] == 1
        assert result["users_count"] == 1
        assert "my-bucket" in result["buckets"]
        assert "admin" in result["users"]
        assert result["secrets"] == ["db-creds"]
        assert result["dynamodb_tables"] == ["Users"]
        # Only the loot-shaped key is flagged, not the stylesheet.
        keys = [o["key"] for o in result["interesting_objects"]]
        assert keys == ["webadmin/id_rsa"]


# --- IAM privesc helpers + finder (from the BlackSky-Hailstorm plays) ---


class TestIamPrivescHelpers:
    def test_flatten_actions_allow_only_and_lowercased(self):
        doc = {
            "Statement": [
                {"Effect": "Allow", "Action": ["iam:PassRole", "S3:GetObject"]},
                {"Effect": "Deny", "Action": "iam:DeleteRole"},
                {"Effect": "Allow", "Action": "lambda:CreateFunction"},
            ]
        }
        actions = _flatten_actions(doc)
        assert "iam:passrole" in actions
        assert "s3:getobject" in actions
        assert "lambda:createfunction" in actions
        assert "iam:deleterole" not in actions  # Deny is ignored

    def test_action_matches_exact_service_and_star_wildcards(self):
        assert _action_matches("iam:passrole", ["iam:passrole"])
        assert _action_matches("iam:setdefaultpolicyversion", ["iam:*"])
        assert _action_matches("iam:passrole", ["*"])
        assert _action_matches("iam:createaccesskey", ["iam:Create*".lower()])
        assert not _action_matches("iam:passrole", ["s3:getobject"])


class TestIamPrivescFinder:
    def _finder(self, tmp_path):
        skill = IamPrivescFinder(target="aws-account")
        skill.loot_path = str(tmp_path)
        skill._artifacts = []
        skill._errors = []
        skill._flags = ""
        skill._user = ""
        skill._role = ""
        return skill

    def test_attach_user_policy_flagged(self, tmp_path):
        """amelia_lambda_policy from the lab -> iam:AttachUserPolicy path."""
        skill = self._finder(tmp_path)
        amelia_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetShardIterator",
                        "iam:AttachUserPolicy",
                        "dynamodb:DescribeStream",
                    ],
                },
            ],
        }

        def fake_run_json(cmd):
            if cmd.startswith("aws iam list-attached-user-policies"):
                return {"AttachedPolicies": [{"PolicyArn": "arn:pol/amelia"}]}
            if cmd.startswith("aws iam list-policy-versions"):
                return {"Versions": [{"VersionId": "v1"}]}
            if cmd.startswith("aws iam get-policy-version"):
                return {"PolicyVersion": {"Document": amelia_doc}}
            return None

        stdout = json.dumps({"Account": "1", "Arn": "arn:aws:iam::1:user/amelia"})
        with patch.object(skill, "_run_json", side_effect=fake_run_json):
            result = skill.parse_output(stdout, "", 0)

        assert skill._user == "amelia"
        actions = {p["action"] for p in result["privesc_paths"]}
        assert "iam:attachuserpolicy" in actions

    def test_passrole_and_createfunction_flagged(self, tmp_path):
        """terraform main.tf resource_access policy -> PassRole + CreateFunction."""
        skill = self._finder(tmp_path)
        tf_doc = {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["lambda:CreateFunction", "iam:PassRole"],
                }
            ]
        }

        def fake_run_json(cmd):
            if cmd.startswith("aws iam list-attached-user-policies"):
                return {"AttachedPolicies": [{"PolicyArn": "arn:pol/tf"}]}
            if cmd.startswith("aws iam list-policy-versions"):
                return {"Versions": [{"VersionId": "v1"}]}
            if cmd.startswith("aws iam get-policy-version"):
                return {"PolicyVersion": {"Document": tf_doc}}
            return None

        stdout = json.dumps({"Account": "1", "Arn": "arn:aws:iam::1:user/deployer"})
        with patch.object(skill, "_run_json", side_effect=fake_run_json):
            result = skill.parse_output(stdout, "", 0)

        actions = {p["action"] for p in result["privesc_paths"]}
        assert {"iam:passrole", "lambda:createfunction"} <= actions

    def test_no_paths_when_policies_benign(self, tmp_path):
        skill = self._finder(tmp_path)
        benign = {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"]}]}

        def fake_run_json(cmd):
            if cmd.startswith("aws iam list-attached-user-policies"):
                return {"AttachedPolicies": [{"PolicyArn": "arn:pol/ro"}]}
            if cmd.startswith("aws iam list-policy-versions"):
                return {"Versions": [{"VersionId": "v1"}]}
            if cmd.startswith("aws iam get-policy-version"):
                return {"PolicyVersion": {"Document": benign}}
            return None

        stdout = json.dumps({"Account": "1", "Arn": "arn:aws:iam::1:user/reader"})
        with patch.object(skill, "_run_json", side_effect=fake_run_json):
            result = skill.parse_output(stdout, "", 0)

        assert result["privesc_count"] == 0

    def test_bad_identity_returns_error(self, tmp_path):
        skill = self._finder(tmp_path)
        result = skill.parse_output("not json", "denied", 1)
        assert "error" in result


class TestGcloudAudit:
    def test_build_command(self):
        skill = GcloudAudit(target="gcp-project")
        cmd = skill.build_command()
        assert "gcloud info --format=json" in cmd
        assert "gcloud projects list --format=json" in cmd

    def test_parse_output(self, tmp_path):
        skill = GcloudAudit(target="gcp-project")
        skill.loot_path = str(tmp_path)
        skill._artifacts = []
        skill._errors = []

        info = json.dumps({"config": {"project": "my-project"}})
        projects = json.dumps([{"projectId": "proj-1"}, {"projectId": "proj-2"}])

        stdout = f"{info}\n---SECTION---\n{projects}"
        result = skill.parse_output(stdout, "", 0)

        assert result["projects_count"] == 2
        assert "proj-1" in result["projects"]

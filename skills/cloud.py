import json

from skills.base import BaseSkill


class AwsCliAudit(BaseSkill):
    """AWS security audit using the AWS CLI."""

    tool = "aws"
    tool_version_command = "aws --version 2>&1"

    def build_command(self, **kwargs) -> str:
        profile = kwargs.get("profile", "")
        self._profile = profile
        profile_flag = f" --profile {profile}" if profile else ""

        # Chain multiple AWS commands: identity, S3 buckets, IAM users
        commands = [
            f"aws sts get-caller-identity --output json{profile_flag}",
            f"aws s3api list-buckets --output json{profile_flag}",
            f"aws iam list-users --output json{profile_flag}",
        ]
        # Use a delimiter between outputs so we can split them
        return " && echo '---SECTION---' && ".join(commands)

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        sections = stdout.split("---SECTION---")

        identity = {}
        buckets = []
        users = []

        if len(sections) >= 1:
            try:
                identity = json.loads(sections[0].strip())
            except (json.JSONDecodeError, IndexError):
                self._errors.append("Failed to parse AWS identity")

        if len(sections) >= 2:
            try:
                data = json.loads(sections[1].strip())
                buckets = [b.get("Name") for b in data.get("Buckets", [])]
            except (json.JSONDecodeError, IndexError):
                self._errors.append("Failed to parse S3 buckets")

        if len(sections) >= 3:
            try:
                data = json.loads(sections[2].strip())
                users = [u.get("UserName") for u in data.get("Users", [])]
            except (json.JSONDecodeError, IndexError):
                self._errors.append("Failed to parse IAM users")

        findings = {
            "identity": identity,
            "buckets_count": len(buckets),
            "buckets": buckets,
            "users_count": len(users),
            "users": users,
        }
        self.save_json("cloud_audit_aws.json", findings)
        return findings


class GcloudAudit(BaseSkill):
    """GCP security audit using gcloud CLI."""

    tool = "gcloud"
    tool_version_command = "gcloud version 2>&1"

    def build_command(self, **kwargs) -> str:
        return (
            "gcloud info --format=json"
            " && echo '---SECTION---' && "
            "gcloud projects list --format=json"
        )

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        sections = stdout.split("---SECTION---")

        config = {}
        projects = []

        if len(sections) >= 1:
            try:
                data = json.loads(sections[0].strip())
                config = data.get("config", {})
            except (json.JSONDecodeError, IndexError):
                self._errors.append("Failed to parse GCP info")

        if len(sections) >= 2:
            try:
                data = json.loads(sections[1].strip())
                projects = [p.get("projectId") for p in data]
            except (json.JSONDecodeError, IndexError):
                self._errors.append("Failed to parse GCP projects")

        findings = {
            "config": config,
            "projects_count": len(projects),
            "projects": projects,
        }
        self.save_json("cloud_audit_gcp.json", findings)
        return findings

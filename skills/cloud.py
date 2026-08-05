import json
import re

from skills.base import BaseSkill

SECTION = "---SECTION---"

# Object keys worth pulling out of an S3 bucket during recon. Case-insensitive.
S3_INTERESTING_KEY = re.compile(
    r"(id_rsa|id_ed25519|\.pem$|\.ppk$|\.key$|\.pfx$|\.p12$|\.env$|"
    r"credential|secret|password|passwd|token|\.kdbx$|\.sql$|\.bak$|"
    r"backup|dump|\.tfstate$|config\.(json|yml|yaml|php)$|\.htpasswd|flag)",
    re.IGNORECASE,
)

# IAM actions that grant (or chain into) privilege escalation. Maps the raw
# action to the escalation technique it enables. Mirrors the primitives seen in
# the BlackSky-Hailstorm lab plus the canonical Rhino Security IAM privesc set.
IAM_PRIVESC_ACTIONS = {
    "iam:setdefaultpolicyversion": "Roll a managed policy back to a more permissive existing version",
    "iam:createpolicyversion": "Publish a new policy version (--set-as-default) granting admin",
    "iam:attachuserpolicy": "Attach AdministratorAccess to a controlled user",
    "iam:attachgrouppolicy": "Attach AdministratorAccess to a group you belong to",
    "iam:attachrolepolicy": "Attach AdministratorAccess to an assumable role",
    "iam:putuserpolicy": "Inline an admin policy onto a user",
    "iam:putgrouppolicy": "Inline an admin policy onto a group",
    "iam:putrolepolicy": "Inline an admin policy onto a role",
    "iam:createaccesskey": "Mint access keys for a more privileged user",
    "iam:createloginprofile": "Set a console password on a user with no profile",
    "iam:updateloginprofile": "Reset another user's console password",
    "iam:addusertogroup": "Join a privileged group",
    "iam:passrole": "Pass a privileged role to a compute service (see lambda/ec2/glue below)",
    "iam:updateassumerolepolicy": "Rewrite a role's trust policy so you can assume it",
    "sts:assumerole": "Assume a role whose trust policy allows you",
    "lambda:createfunction": "Run code as a passed role (pair with iam:PassRole)",
    "lambda:invokefunction": "Trigger the privileged function you created",
    "lambda:updatefunctioncode": "Overwrite an existing privileged function's code",
    "lambda:createeventsourcemapping": "Wire a stream/queue to invoke a privileged function",
    "ec2:runinstances": "Launch an instance with a passed instance profile",
    "cloudformation:createstack": "Deploy a stack that passes a privileged role",
    "glue:createdevendpoint": "Create a Glue dev endpoint running as a passed role",
    "sagemaker:createnotebookinstance": "Create a notebook that assumes a passed role",
    "ssm:sendcommand": "Run commands as root on SSM-managed instances",
    "ssm:startsession": "Open an interactive session on SSM-managed instances",
}


def _flatten_actions(document: dict) -> list[str]:
    """Return the lowercased Action list from a policy document (Allow only)."""
    actions: list[str] = []
    statements = document.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]
    for stmt in statements:
        if not isinstance(stmt, dict):
            continue
        if stmt.get("Effect") != "Allow":
            continue
        raw = stmt.get("Action", [])
        if isinstance(raw, str):
            raw = [raw]
        actions.extend(a.lower() for a in raw if isinstance(a, str))
    return actions


def _action_matches(privesc_action: str, granted: list[str]) -> bool:
    """True if a granted action (possibly a wildcard) covers privesc_action."""
    service = privesc_action.split(":", 1)[0]
    for g in granted:
        if g == "*" or g == privesc_action or g == f"{service}:*":
            return True
        # prefix wildcards e.g. "iam:Create*"
        if g.endswith("*") and privesc_action.startswith(g[:-1]):
            return True
    return False


class AwsCliAudit(BaseSkill):
    """AWS recon + loot: identity, S3 objects, IAM, Secrets Manager, DynamoDB."""

    tool = "aws"
    tool_version_command = "aws --version 2>&1"

    def _flags(self, kwargs) -> str:
        profile = kwargs.get("profile", "")
        region = kwargs.get("region", "")
        flags = ""
        if profile:
            flags += f" --profile {profile}"
        if region:
            flags += f" --region {region}"
        return flags

    def build_command(self, **kwargs) -> str:
        f = self._flags(kwargs)
        self._cli_flags = f
        self._max_buckets = int(kwargs.get("max_buckets", 20))
        commands = [
            f"aws sts get-caller-identity --output json{f}",
            f"aws s3api list-buckets --output json{f}",
            f"aws iam list-users --output json{f}",
            f"aws secretsmanager list-secrets --output json{f}",
            f"aws dynamodb list-tables --output json{f}",
        ]
        return f" && echo '{SECTION}' && ".join(commands)

    def _safe_json(self, blob: str, label: str):
        try:
            return json.loads(blob.strip())
        except (json.JSONDecodeError, ValueError):
            self._errors.append(f"Failed to parse {label}")
            return None

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        sections = stdout.split(SECTION)
        get = lambda i: sections[i] if i < len(sections) else ""

        identity = self._safe_json(get(0), "AWS identity") or {}

        buckets = []
        bdata = self._safe_json(get(1), "S3 buckets")
        if bdata:
            buckets = [b.get("Name") for b in bdata.get("Buckets", [])]

        users = []
        udata = self._safe_json(get(2), "IAM users")
        if udata:
            users = [u.get("UserName") for u in udata.get("Users", [])]

        secrets = []
        sdata = self._safe_json(get(3), "Secrets Manager list")
        if sdata:
            secrets = [s.get("Name") for s in sdata.get("SecretList", [])]

        tables = []
        ddata = self._safe_json(get(4), "DynamoDB tables")
        if ddata:
            tables = ddata.get("TableNames", [])

        interesting_objects = self._scan_buckets(buckets)

        findings = {
            "identity": identity,
            "buckets_count": len(buckets),
            "buckets": buckets,
            "users_count": len(users),
            "users": users,
            "secrets_count": len(secrets),
            "secrets": secrets,
            "dynamodb_tables": tables,
            "interesting_objects": interesting_objects,
        }
        self.save_json("cloud_audit_aws.json", findings)
        return findings

    def _scan_buckets(self, buckets: list[str]) -> list[dict]:
        """Recurse each bucket and flag object keys that look like loot."""
        # Defaults let parse_output run even if build_command wasn't called first.
        max_buckets = getattr(self, "_max_buckets", 20)
        cli_flags = getattr(self, "_cli_flags", "")
        hits: list[dict] = []
        for bucket in buckets[:max_buckets]:
            if not bucket:
                continue
            cmd = (
                f"aws s3 ls s3://{bucket} --recursive{cli_flags} "
                f"2>/dev/null | head -n 2000"
            )
            result = self.execute_shell(cmd, timeout=60)
            listing = result.get("stdout", "") if isinstance(result, dict) else ""
            for line in listing.splitlines():
                # `aws s3 ls --recursive` -> "DATE TIME SIZE key/path"
                parts = line.split(None, 3)
                if len(parts) < 4:
                    continue
                key = parts[3]
                if S3_INTERESTING_KEY.search(key):
                    hits.append({"bucket": bucket, "key": key, "size": parts[2]})
        return hits


class IamPrivescFinder(BaseSkill):
    """Enumerate the caller's IAM policies and flag privilege-escalation paths."""

    tool = "aws"
    tool_version_command = "aws --version 2>&1"

    def build_command(self, **kwargs) -> str:
        profile = kwargs.get("profile", "")
        region = kwargs.get("region", "")
        self._flags = ""
        if profile:
            self._flags += f" --profile {profile}"
        if region:
            self._flags += f" --region {region}"
        # Explicit override, else derived from sts identity in parse_output.
        self._user = kwargs.get("user", "")
        self._role = kwargs.get("role", "")
        return f"aws sts get-caller-identity --output json{self._flags}"

    def _run_json(self, cmd: str):
        """Best-effort aws call: return parsed JSON or None (AccessDenied etc.)."""
        result = self.execute_shell(cmd + self._flags + " --output json", timeout=45)
        out = result.get("stdout", "") if isinstance(result, dict) else ""
        if not out.strip():
            return None
        try:
            return json.loads(out)
        except (json.JSONDecodeError, ValueError):
            return None

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        try:
            identity = json.loads(stdout.strip())
        except (json.JSONDecodeError, ValueError):
            self._errors.append("Could not resolve caller identity")
            return {"error": "sts get-caller-identity failed", "stderr": stderr.strip()}

        arn = identity.get("Arn", "")
        # Derive principal type/name from the ARN when not passed explicitly.
        if not self._user and ":user/" in arn:
            self._user = arn.split("/")[-1]
        if not self._role and ":assumed-role/" in arn:
            self._role = arn.split("/")[-2]

        policy_docs: list[dict] = []  # {"source": str, "document": {...}}
        self._collect_user_policies(policy_docs)
        self._collect_role_policies(policy_docs)

        flagged = self._flag_privesc(policy_docs)

        findings = {
            "identity": identity,
            "user": self._user,
            "role": self._role,
            "policies_examined": [p["source"] for p in policy_docs],
            "privesc_paths": flagged,
            "privesc_count": len(flagged),
        }
        self.save_json("iam_privesc_paths.json", findings)
        return findings

    def _collect_managed_policy(self, arn: str, docs: list[dict]):
        meta = self._run_json(f"aws iam get-policy --policy-arn {arn}")
        default_ver = None
        if meta:
            default_ver = meta.get("Policy", {}).get("DefaultVersionId")
        versions = self._run_json(f"aws iam list-policy-versions --policy-arn {arn}")
        version_ids = []
        if versions:
            version_ids = [v.get("VersionId") for v in versions.get("Versions", [])]
        for vid in version_ids:
            doc = self._run_json(
                f"aws iam get-policy-version --policy-arn {arn} --version-id {vid}"
            )
            if not doc:
                continue
            document = doc.get("PolicyVersion", {}).get("Document", {})
            tag = "default" if vid == default_ver else "non-default"
            docs.append({"source": f"managed:{arn}#{vid}({tag})", "document": document})

    def _collect_user_policies(self, docs: list[dict]):
        if not self._user:
            return
        attached = self._run_json(
            f"aws iam list-attached-user-policies --user-name {self._user}"
        )
        if attached:
            for p in attached.get("AttachedPolicies", []):
                self._collect_managed_policy(p["PolicyArn"], docs)
        inline = self._run_json(
            f"aws iam list-user-policies --user-name {self._user}"
        )
        if inline:
            for name in inline.get("PolicyNames", []):
                doc = self._run_json(
                    f"aws iam get-user-policy --user-name {self._user} --policy-name {name}"
                )
                if doc:
                    docs.append(
                        {
                            "source": f"inline:user/{self._user}/{name}",
                            "document": doc.get("PolicyDocument", {}),
                        }
                    )

    def _collect_role_policies(self, docs: list[dict]):
        if not self._role:
            return
        attached = self._run_json(
            f"aws iam list-attached-role-policies --role-name {self._role}"
        )
        if attached:
            for p in attached.get("AttachedPolicies", []):
                self._collect_managed_policy(p["PolicyArn"], docs)
        inline = self._run_json(
            f"aws iam list-role-policies --role-name {self._role}"
        )
        if inline:
            for name in inline.get("PolicyNames", []):
                doc = self._run_json(
                    f"aws iam get-role-policy --role-name {self._role} --policy-name {name}"
                )
                if doc:
                    docs.append(
                        {
                            "source": f"inline:role/{self._role}/{name}",
                            "document": doc.get("PolicyDocument", {}),
                        }
                    )

    def _flag_privesc(self, docs: list[dict]) -> list[dict]:
        flagged: list[dict] = []
        for entry in docs:
            granted = _flatten_actions(entry["document"])
            for action, technique in IAM_PRIVESC_ACTIONS.items():
                if _action_matches(action, granted):
                    flagged.append(
                        {
                            "action": action,
                            "technique": technique,
                            "source": entry["source"],
                        }
                    )
        return flagged


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

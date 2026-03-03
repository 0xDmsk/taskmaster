import json
from skills.base import BaseSkill

class CloudAuditSkill(BaseSkill):
    """
    Cloud Audit Skill.
    Checks AWS and GCP configuration.
    """
    def run(self, provider="aws", profile=None, **kwargs):
        results = {
            "provider": provider,
            "status": "Running",
            "findings": []
        }

        if provider == "aws":
            results.update(self._aws_audit(profile))
        elif provider == "gcp":
            results.update(self._gcp_audit(profile))
        else:
            return {"error": f"Unknown provider: {provider}"}

        self.save_json(f"cloud_audit_{provider}.json", results)
        return results

    def _aws_audit(self, profile):
        print("[*] Auditing AWS...")
        
        # 1. WhoAmI
        cmd_who = "aws sts get-caller-identity --output json"
        if profile:
            cmd_who += f" --profile {profile}"
        
        who = self.execute_shell(cmd_who)
        if who["exit_code"] != 0:
            return {"error": "Failed to get AWS identity. Check credentials."}
        
        identity = json.loads(who["stdout"])
        
        # 2. List S3 Buckets
        cmd_s3 = "aws s3 ls --output json"
        if profile:
            cmd_s3 += f" --profile {profile}"
        
        s3 = self.execute_shell(cmd_s3)
        buckets = []
        if s3["exit_code"] == 0:
            buckets = json.loads(s3["stdout"]).get("Buckets", [])
            
        # 3. List IAM Users (if permitted)
        cmd_iam = "aws iam list-users --output json"
        if profile:
            cmd_iam += f" --profile {profile}"
        
        iam = self.execute_shell(cmd_iam)
        users = []
        if iam["exit_code"] == 0:
            users = json.loads(iam["stdout"]).get("Users", [])

        return {
            "identity": identity,
            "buckets_count": len(buckets),
            "users_count": len(users),
            "users": [u.get("UserName") for u in users],
            "buckets": [b.get("Name") for b in buckets]
        }

    def _gcp_audit(self, profile):
        print("[*] Auditing GCP...")
        
        # 1. Info
        cmd_info = "gcloud info --format=json"
        info = self.execute_shell(cmd_info)
        if info["exit_code"] != 0:
            return {"error": "Failed to get GCP info."}
            
        config = json.loads(info["stdout"])
        
        # 2. List Projects
        cmd_proj = "gcloud projects list --format=json"
        proj = self.execute_shell(cmd_proj)
        projects = []
        if proj["exit_code"] == 0:
            projects = json.loads(proj["stdout"])

        return {
            "config": config.get("config", {}),
            "projects_count": len(projects),
            "projects": [p.get("projectId") for p in projects]
        }

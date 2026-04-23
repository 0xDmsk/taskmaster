"""
seed_dashboard.py — Development-only dashboard fixture generator.

Populates the Taskmaster state database with synthetic security assessment
data so you can inspect the dashboard UI without running a real engagement.

ALL data in this script is FICTIONAL:
  - Target IPs are RFC 1918 private addresses used as placeholders.
  - Skill names (git_dumper, ftp_exploit, etc.) do not exist in skills/.
  - Credentials shown in findings (e.g. DB_PASS=s3cr3tP@ss) are fabricated.

WARNING: Do NOT run this against a production or active-assessment database.
It writes directly to the state store and will corrupt real audit trails.
Use only on a clean/dev instance (run `make clean` first if needed).

Usage:
    uv run python scripts/seed_dashboard.py
    make start   # then open http://localhost:5000
"""

import json
import sys
import os
import uuid
from datetime import datetime, timedelta

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state.storage import append_execution

TARGETS = ["192.168.1.10", "192.168.1.20", "10.0.0.5"]
PHASES = ["reconnaissance", "enumeration", "exploitation", "post_exploitation", "reporting"]

BASE_TIME = datetime.utcnow() - timedelta(hours=3)


def ts(offset_minutes):
    return (BASE_TIME + timedelta(minutes=offset_minutes)).isoformat()


EXECUTIONS = [
    # ── 192.168.1.10 – full completed run ──────────────────────────────────
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.10",
        "security_phase": "reconnaissance",
        "status": "COMPLETED",
        "created_at": ts(0), "created_by": "gemini-agent",
        "updated_at": ts(3), "updated_by": "kali-operator",
        "executor_id": "kali-001",
        "request": {"skill": "nmap_scan", "justification": "Initial host discovery and port scan", "action_type": "skill"},
        "result": json.dumps({
            "skill": "nmap_scan", "target": "192.168.1.10", "status": "success",
            "findings": {
                "severity": "info",
                "description": "Host is up. Open ports: 22/ssh, 80/http, 443/https, 3306/mysql",
                "risk": "Surface area larger than expected — MySQL exposed.",
                "remediation": "Restrict MySQL (3306) to localhost or VPN range.",
                "cvss": "3.1",
                "references": ["https://nmap.org/book/man-port-specification.html"],
            },
            "artifacts": ["nmap_192.168.1.10.xml", "nmap_192.168.1.10.txt"],
            "errors": [],
        }),
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.10",
        "security_phase": "enumeration",
        "status": "COMPLETED",
        "created_at": ts(5), "created_by": "gemini-agent",
        "updated_at": ts(9), "updated_by": "kali-operator",
        "executor_id": "kali-001",
        "request": {"skill": "gobuster_dir", "justification": "Enumerate web directories on port 80", "action_type": "skill"},
        "result": json.dumps({
            "skill": "gobuster_dir", "target": "192.168.1.10", "status": "success",
            "findings": {
                "severity": "medium",
                "description": "Found /admin (200), /backup (403), /uploads (200), /.git (200)",
                "risk": "/.git directory exposed — full source code and credentials may be leaked.",
                "remediation": "Block /.git in web server config and rotate any secrets found in history.",
                "cvss": "6.5",
                "references": ["https://owasp.org/www-project-web-security-testing-guide/"],
            },
            "artifacts": ["gobuster_192.168.1.10_80.txt"],
            "errors": [],
        }),
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.10",
        "security_phase": "exploitation",
        "status": "COMPLETED",
        "created_at": ts(12), "created_by": "gemini-agent",
        "updated_at": ts(18), "updated_by": "kali-operator",
        "executor_id": "kali-001",
        "request": {"skill": "git_dumper", "justification": "Dump .git directory and extract secrets", "action_type": "skill"},
        "result": json.dumps({
            "skill": "git_dumper", "target": "192.168.1.10", "status": "success",
            "findings": {
                "severity": "critical",
                "description": "Extracted DB credentials from .env in git history: DB_PASS=s3cr3tP@ss",
                "risk": "Full database compromise possible with recovered credentials.",
                "remediation": "Rotate credentials immediately. Purge secret from git history with git-filter-repo.",
                "cvss": "9.1",
                "references": ["https://trufflesecurity.com/blog/dont-commit-secrets"],
            },
            "artifacts": ["git_dump_192.168.1.10.tar.gz", "secrets_found.txt"],
            "errors": [],
        }),
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.10",
        "security_phase": "post_exploitation",
        "status": "COMPLETED",
        "created_at": ts(20), "created_by": "gemini-agent",
        "updated_at": ts(26), "updated_by": "kali-operator",
        "executor_id": "kali-001",
        "request": {"skill": "mysql_enum", "justification": "Enumerate MySQL with recovered credentials", "action_type": "skill"},
        "result": json.dumps({
            "skill": "mysql_enum", "target": "192.168.1.10", "status": "success",
            "findings": {
                "severity": "critical",
                "description": "Authenticated to MySQL as root. Databases: app_db, user_db, logs. PII tables found in user_db.",
                "risk": "Full data exfiltration of PII including emails and hashed passwords.",
                "remediation": "Revoke remote root login. Enforce least-privilege DB accounts.",
                "cvss": "9.8",
                "references": ["https://dev.mysql.com/doc/refman/8.0/en/security-guidelines.html"],
            },
            "artifacts": ["mysql_dump_user_db.sql"],
            "errors": [],
        }),
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.10",
        "security_phase": "reporting",
        "status": "COMPLETED",
        "created_at": ts(28), "created_by": "gemini-agent",
        "updated_at": ts(30), "updated_by": "kali-operator",
        "executor_id": "kali-001",
        "request": {"skill": "generate_report", "justification": "Compile final assessment report", "action_type": "skill"},
        "result": json.dumps({
            "skill": "generate_report", "target": "192.168.1.10", "status": "success",
            "findings": ["Critical: Git exposure with DB creds", "Critical: Remote MySQL root access", "Medium: Exposed /uploads dir"],
            "artifacts": ["report_192.168.1.10.md", "report_192.168.1.10.pdf"],
            "errors": [],
        }),
    },

    # ── 192.168.1.20 – partial run, exploitation failed ────────────────────
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.20",
        "security_phase": "reconnaissance",
        "status": "COMPLETED",
        "created_at": ts(10), "created_by": "gemini-agent",
        "updated_at": ts(13), "updated_by": "kali-operator",
        "executor_id": "kali-002",
        "request": {"skill": "nmap_scan", "justification": "Initial host discovery", "action_type": "skill"},
        "result": json.dumps({
            "skill": "nmap_scan", "target": "192.168.1.20", "status": "success",
            "findings": {
                "severity": "info",
                "description": "Open ports: 21/ftp, 22/ssh, 8080/http-proxy",
                "risk": "FTP on port 21 may allow anonymous login.",
                "remediation": "Disable anonymous FTP. Prefer SFTP over FTP.",
                "cvss": "4.3",
                "references": [],
            },
            "artifacts": ["nmap_192.168.1.20.xml"],
            "errors": [],
        }),
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.20",
        "security_phase": "enumeration",
        "status": "COMPLETED",
        "created_at": ts(15), "created_by": "gemini-agent",
        "updated_at": ts(19), "updated_by": "kali-operator",
        "executor_id": "kali-002",
        "request": {"skill": "ftp_anon_check", "justification": "Check for anonymous FTP login", "action_type": "skill"},
        "result": json.dumps({
            "skill": "ftp_anon_check", "target": "192.168.1.20", "status": "success",
            "findings": {
                "severity": "high",
                "description": "Anonymous FTP login allowed. Readable directories: /pub, /incoming",
                "risk": "Sensitive files readable/writable without authentication.",
                "remediation": "Disable anonymous FTP access in vsftpd.conf.",
                "cvss": "7.5",
                "references": ["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-1999-0497"],
            },
            "artifacts": ["ftp_listing_192.168.1.20.txt"],
            "errors": [],
        }),
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.20",
        "security_phase": "exploitation",
        "status": "FAILED",
        "created_at": ts(22), "created_by": "gemini-agent",
        "updated_at": ts(24), "updated_by": "kali-operator",
        "executor_id": "kali-002",
        "request": {"skill": "ftp_exploit", "justification": "Attempt authenticated FTP exploit", "action_type": "skill"},
        "result": json.dumps({
            "skill": "ftp_exploit", "target": "192.168.1.20", "status": "failure",
            "findings": [],
            "artifacts": [],
            "errors": ["Connection timed out after 30s. Target may have IDS/firewall blocking exploit traffic."],
        }),
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "192.168.1.20",
        "security_phase": "exploitation",
        "status": "QUEUED",
        "created_at": ts(25), "created_by": "gemini-agent",
        "updated_at": ts(25), "updated_by": None,
        "executor_id": None,
        "request": {"skill": "ssh_bruteforce", "justification": "Attempt SSH credential stuffing with common wordlist", "action_type": "skill"},
        "result": None,
    },

    # ── 10.0.0.5 – active run ──────────────────────────────────────────────
    {
        "execution_id": str(uuid.uuid4()),
        "target": "10.0.0.5",
        "security_phase": "reconnaissance",
        "status": "COMPLETED",
        "created_at": ts(35), "created_by": "gemini-agent",
        "updated_at": ts(38), "updated_by": "kali-operator",
        "executor_id": "kali-003",
        "request": {"skill": "nmap_scan", "justification": "Initial recon on internal target", "action_type": "skill"},
        "result": json.dumps({
            "skill": "nmap_scan", "target": "10.0.0.5", "status": "success",
            "findings": {
                "severity": "info",
                "description": "Open ports: 80/http, 443/https, 8443/https-alt, 9200/elasticsearch",
                "risk": "Elasticsearch on 9200 may be unauthenticated.",
                "remediation": "Enable Elasticsearch security features (xpack.security.enabled: true).",
                "cvss": "5.3",
                "references": ["https://www.elastic.co/guide/en/elasticsearch/reference/current/security-minimal-setup.html"],
            },
            "artifacts": ["nmap_10.0.0.5.xml"],
            "errors": [],
        }),
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "10.0.0.5",
        "security_phase": "enumeration",
        "status": "RUNNING",
        "created_at": ts(40), "created_by": "gemini-agent",
        "updated_at": ts(41), "updated_by": "kali-operator",
        "executor_id": "kali-003",
        "request": {"skill": "elasticsearch_enum", "justification": "Enumerate Elasticsearch indices", "action_type": "skill"},
        "result": None,
    },
    {
        "execution_id": str(uuid.uuid4()),
        "target": "10.0.0.5",
        "security_phase": "exploitation",
        "status": "QUEUED",
        "created_at": ts(41), "created_by": "gemini-agent",
        "updated_at": ts(41), "updated_by": None,
        "executor_id": None,
        "request": {"skill": "elasticsearch_exploit", "justification": "Attempt unauthenticated data dump", "action_type": "skill"},
        "result": None,
    },
]


def main():
    print(f"Seeding {len(EXECUTIONS)} executions...")
    for rec in EXECUTIONS:
        try:
            append_execution(rec)
            print(f"  + {rec['target']} / {rec['security_phase']} / {rec['status']}")
        except Exception as e:
            print(f"  ! {rec['target']} / {rec['security_phase']}: {e}")
    print("Done.")


if __name__ == "__main__":
    main()

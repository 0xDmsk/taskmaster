import os

# Where taskmaster code lives — skills, policies, tools, Dockerfile, templates.
# Always derived from this file's location.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Where assessment output goes — runtime state, audit logs, loot, reports.
# Configurable via TASKMASTER_WORK_DIR env var, defaults to cwd.
WORK_DIR = os.environ.get("TASKMASTER_WORK_DIR", os.getcwd())

# All runtime artifacts live under a single `runtime/` umbrella inside
# WORK_DIR. Keeps an engagement folder tidy (one directory to gitignore,
# one to delete) and dodges the namespace collision between the on-disk
# state directory and the `state/` Python package in PROJECT_DIR.
RUNTIME_DIR = os.path.join(WORK_DIR, "runtime")
LOOT_DIR = os.path.join(RUNTIME_DIR, "loot")
REPORTS_DIR = os.path.join(RUNTIME_DIR, "reports")
AUDIT_DIR = os.path.join(RUNTIME_DIR, "audit")
STATE_DIR = os.path.join(RUNTIME_DIR, "state")

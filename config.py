import os

# Where taskmaster code lives — skills, policies, tools, Dockerfile, templates.
# Always derived from this file's location.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Where assessment output goes — state DB, audit logs, loot.
# Configurable via TASKMASTER_WORK_DIR env var, defaults to cwd.
WORK_DIR = os.environ.get("TASKMASTER_WORK_DIR", os.getcwd())

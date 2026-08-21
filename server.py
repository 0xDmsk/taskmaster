import argparse
import json
import logging
import os
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import config
from tools.request_security_action import handle_request
from tools.request_playbook import handle_request_playbook
from tools.request_batch import handle_request_batch
from tools.get_operational_guide import core_instructions, handle_get_operational_guide
from tools.suggest_next_action import handle_suggest_next_action
from tools.query_execution_status import handle_query_execution_status
from tools.fetch_execution_result import handle_fetch_execution_result
from tools.mark_execution_complete import handle_mark_execution_complete
from tools.claim_execution import handle_claim_execution
from tools.start_execution import handle_start_execution
from tools.complete_execution import handle_complete_execution
from tools.fail_execution import handle_fail_execution
from tools.list_queued_executions import handle_list_queued_executions
from tools.spawn_agent import handle_spawn_agent
from tools.cleanup_agents import handle_cleanup_agents
from tools.recover_execution import handle_recover_execution
from tools.wait_for_completion import handle_wait_for_completion
from tools.reaper import start_reaper_thread
from tools.create_reporting_engagement import handle_create_reporting_engagement
from tools.list_reporting_engagements import handle_list_reporting_engagements
from tools.create_reporting_finding import handle_create_reporting_finding
from tools.get_reporting_finding import handle_get_reporting_finding
from tools.list_reporting_findings import handle_list_reporting_findings
from tools.request_reporting_docx import handle_request_reporting_docx
from tools.update_reporting_finding import handle_update_reporting_finding
from tools.add_reporting_finding_evidence import handle_add_reporting_finding_evidence
from tools.add_reporting_finding_reference import handle_add_reporting_finding_reference
from tools.assemble_threat_model_context import handle_assemble_threat_model_context
from tools.create_threat_model import handle_create_threat_model
from tools.list_threat_models import handle_list_threat_models
from tools.get_threat_model import handle_get_threat_model
from tools.update_threat_model import handle_update_threat_model
from tools.add_threat_model_entry import handle_add_threat_model_entry
from tools.update_threat_model_entry import handle_update_threat_model_entry
from tools.delete_threat_model_entry import handle_delete_threat_model_entry
from tools.export_threat_model_markdown import handle_export_threat_model_markdown
from state.reporting import FINDING_CATEGORY_ORDER


def load_tool_schema(tool_name):
    """Load tool schema from JSON file if it exists."""
    schema_path = os.path.join(config.PROJECT_DIR, "tools", f"{tool_name}.json")
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            return json.load(f)
    return None


TOOLS = {
    "request_security_action": {
        "description": (
            "Request execution of a security-related action. (New to this Taskmaster "
            "session? Call get_operational_guide first for the full workflow.) Commands "
            "are validated against macOS VM platform constraints — raw-socket scans "
            "(nmap -sS, -sU, -O) are blocked. Use nmap -sT. This tool only queues work; "
            "after it returns QUEUED, spawn or reuse a compatible agent, then monitor "
            "with wait_for_completion."
        ),
        "handler": handle_request,
        "schema": load_tool_schema("request_security_action"),
    },
    "suggest_next_action": {
        "description": (
            "Inspect current state (optionally scoped to an engagement_id) and return a "
            "prioritized list of concrete next actions: failed work to review, completed "
            "executions missing an interpretation, ready work waiting for a worker, "
            "observations not yet triaged into findings, findings missing required report "
            "fields, phase-coverage gaps, and threat-model status. Read-only. Use it to "
            "orient at the start of a session or whenever you're deciding what to do next."
        ),
        "handler": handle_suggest_next_action,
        "inputSchema": {
            "type": "object",
            "properties": {
                "engagement_id": {
                    "type": "string",
                    "description": "Optional engagement id to scope the analysis to.",
                }
            },
        },
    },
    "get_operational_guide": {
        "description": (
            "Return the full Taskmaster operational guide — the canonical workflow "
            "for orchestration, playbooks/dependencies, note-taking discipline, the "
            "bot-protection escalation ladder, the reporting-database flow, and the "
            "threat-modeling process. Call this once at the start of an assessment "
            "(the MCP handshake only carries a short core), and whenever you need the "
            "detailed reporting or threat-model steps."
        ),
        "handler": handle_get_operational_guide,
        "inputSchema": {"type": "object", "properties": {}},
    },
    "request_playbook": {
        "description": (
            "(New to this Taskmaster session? Call get_operational_guide first.) "
            "Queue a named playbook (or an inline list of steps) as a dependency "
            "chain against one target. Each step runs only after the previous one "
            "COMPLETES; if a step fails, the rest of the chain is cancelled. Call "
            "with no 'playbook'/'steps' to list the built-in playbooks. Prefer this "
            "over issuing several request_security_action calls by hand when the "
            "steps are ordered. After queuing, spawn a compatible agent and monitor "
            "the last execution_id with wait_for_completion."
        ),
        "handler": handle_request_playbook,
        "inputSchema": {
            "type": "object",
            "required": ["target"],
            "properties": {
                "target": {
                    "type": "string",
                    "description": "IP, hostname, or URL the whole chain runs against.",
                },
                "playbook": {
                    "type": "string",
                    "description": (
                        "Name of a built-in playbook (e.g. 'web-recon', "
                        "'subdomain-recon'). Omit both playbook and steps to list them."
                    ),
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Inline ordered steps, each a partial request_security_action "
                        "payload (phase, agent_role, action_type, skill/command/script, "
                        "arguments, justification, expected_output). target/engagement_id/"
                        "depends_on are filled in automatically. Ignored if 'playbook' is set."
                    ),
                },
                "engagement_id": {
                    "type": "string",
                    "description": "Optional reporting engagement id applied to every step.",
                },
            },
        },
    },
    "request_batch": {
        "description": (
            "Fan ONE skill out over many bounded shards — one execution per shard — "
            "to tackle work that will never fit a single execution window (a full "
            "nuclei scan split by template group, enumeration over a large scope). "
            "Unlike request_playbook (heterogeneous steps, one target, always "
            "chained), this queues the SAME step across a 'shards' list. Shards on "
            "different targets run in parallel across workers; for shards on the SAME "
            "target pass sequential=true so they chain (the per-target lock serializes "
            "same-target work anyway). Each shard writes its own envelope/artifacts; "
            "aggregate in your notes. Spawn one or more compatible agents afterward."
        ),
        "handler": handle_request_batch,
        "inputSchema": {
            "type": "object",
            "required": ["action_type", "phase", "agent_role", "shards", "justification"],
            "properties": {
                "target": {
                    "type": "string",
                    "description": (
                        "Base target for shards that don't set their own. Same-target "
                        "shards need sequential=true."
                    ),
                },
                "action_type": {
                    "type": "string",
                    "description": "Execution type applied to every shard (e.g. 'mobile_skill', 'skill').",
                },
                "skill": {
                    "type": "string",
                    "description": "Skill class path applied to every shard (e.g. 'mobile.MobileNucleiScan').",
                },
                "phase": {"type": "string", "description": "Security phase for every shard."},
                "agent_role": {"type": "string", "description": "Agent role for every shard."},
                "arguments": {
                    "type": "object",
                    "description": "Base skill arguments; each shard's arguments shallow-merge over these.",
                    "additionalProperties": True,
                },
                "shards": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "One entry per bounded unit of work. Each may set 'target', "
                        "'arguments' (merged over base), 'label', and extra 'depends_on'. "
                        "e.g. nuclei by template group: "
                        '[{"label":"android","arguments":{"templates":"/opt/mobile-nuclei-templates/Android"}}, ...]'
                    ),
                },
                "sequential": {
                    "type": "boolean",
                    "description": (
                        "Chain shards (each after the previous COMPLETES). Use for "
                        "same-target work; leave false for different-target parallel fan-out."
                    ),
                },
                "justification": {"type": "string", "minLength": 50},
                "expected_output": {"type": "string"},
                "engagement_id": {"type": "string"},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Prerequisite execution_ids applied to every shard.",
                },
            },
        },
    },
    "spawn_agent": {
        "description": (
            "Spawn a new agent container for a specific target or task. This is the "
            "default next step after request_security_action unless you have already "
            "verified a compatible live worker for that target."
        ),
        "handler": handle_spawn_agent,
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["kali", "playwright", "reporting", "mobile"],
                    "description": (
                        "Executor type to launch. Use 'kali' for CLI/python tasks, "
                        "'playwright' for browser-rendered tasks, 'reporting' "
                        "for rendering client-facing deliverables via 'report_skill' "
                        "actions (e.g. reporting.FindingDocxReport), or 'mobile' for "
                        "Android APK static analysis via 'mobile_skill' actions "
                        "(e.g. mobile.ManifestScan)."
                    ),
                },
                "interactive_browser": {
                    "type": "boolean",
                    "description": (
                        "When using a Playwright agent, expose a local noVNC browser "
                        "session for manual interaction. Defaults to true for "
                        "Playwright agents."
                    ),
                },
                "browser_engine": {
                    "type": "string",
                    "enum": ["playwright", "patchright", "camoufox"],
                    "description": (
                        "Which browser stack the Playwright agent should use. "
                        "'patchright' (default) is a Playwright drop-in with "
                        "anti-detection patches on Chromium; pick it first. "
                        "'camoufox' is a custom Firefox tuned for fingerprint "
                        "resistance — escalate to it when patchright still gets "
                        "blocked (ERR_HTTP2_PROTOCOL_ERROR, silent 403, visible "
                        "challenge page). 'playwright' is vanilla Chromium and "
                        "should only be used when you specifically need a "
                        "non-patched baseline."
                    ),
                },
                "interactive_hold_ms": {
                    "type": "integer",
                    "description": (
                        "How long browser skills should keep an interactive "
                        "Playwright session open for manual input before collecting "
                        "final observations."
                    ),
                },
                "novnc_port": {
                    "type": "integer",
                    "description": (
                        "Optional host port to bind the Playwright noVNC session "
                        "to. If omitted, a free localhost port is selected."
                    ),
                },
                "target": {
                    "type": "string",
                    "description": "IP, hostname, or URL to assign to the agent",
                },
                "mission": {
                    "type": "string",
                    "description": "Mission briefing text for the agent",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Custom agent/container name (auto-generated if omitted)",
                },
                "taskmaster_host": {
                    "type": "string",
                    "description": "Override Taskmaster host IP",
                },
                "taskmaster_port": {
                    "type": "string",
                    "description": "Override Taskmaster port",
                },
                "proxy_url": {
                    "type": "string",
                    "description": (
                        "HTTP proxy URL for the container (e.g. "
                        "http://host.docker.internal:8080 for Burp Suite). "
                        "Off by default — only set this when the user has "
                        "asked to route traffic through an intercepting "
                        "proxy. When set, the container's HTTP/HTTPS_PROXY "
                        "env vars are populated and proxychains4 is "
                        "configured to match."
                    ),
                },
                "session_dir": {
                    "type": "string",
                    "description": (
                        "Absolute host path to a directory of user-supplied "
                        "session material (cookie exports, auth tokens, a "
                        "Playwright storage_state.json) to mount read-only at "
                        "/session in the agent. Use this to point at a folder "
                        "inside your engagement/project directory when the "
                        "Taskmaster server's working directory differs from "
                        "where you run — the path is resolved on the server "
                        "host. Must be an absolute path to an existing "
                        "directory. Defaults to <WORK_DIR>/runtime/session. "
                        "Never paste session contents into the mission or "
                        "other arguments; reference files by their /session "
                        "path instead."
                    ),
                },
            },
        },
    },
    "query_execution_status": {
        "description": (
            "Get current status of an execution by execution_id. Returns a slim "
            "projection by default (status, phase, executor, seconds_since_update, "
            "and boolean flags for whether result/interpretation are populated) — "
            "use fetch_execution_result to read the actual result body. Pass "
            "verbose=true to get the full execution record. Prefer "
            "wait_for_completion for the standard workflow; use this mainly for "
            "debugging, recovery, or explicit spot-checks."
        ),
        "handler": handle_query_execution_status,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id"],
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "The execution ID to query",
                },
                "verbose": {
                    "type": "boolean",
                    "description": (
                        "If true, include the full execution record "
                        "(request payload, result body, interpretation). "
                        "Default false — keeps responses small."
                    ),
                },
            },
        },
    },
    "fetch_execution_result": {
        "description": "Fetch result for a completed/failed execution",
        "handler": handle_fetch_execution_result,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id"],
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "The execution ID to fetch results for",
                },
            },
        },
    },
    "mark_execution_complete": {
        "description": "Mark an execution as completed or failed (generic)",
        "handler": handle_mark_execution_complete,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {"type": "string"},
                "result": {
                    "type": "string",
                    "description": "Result text or error info",
                },
                "interpretation": {
                    "type": "string",
                    "description": (
                        "Natural-language analysis of the result the calling LLM produced "
                        "after reviewing the raw output. Markdown is supported. "
                        "Surfaced in the dashboard above the raw observations. "
                        "Voice: pentester drafting working notes — plain and concrete, "
                        "cite the URL/header/parameter/payload that proves the claim instead "
                        "of abstract risk language. No scaremongering, no marketing tone. "
                        "Length follows the observation; a few sentences is often enough. "
                        "Full tone contract in policies/note_taking_template.md."
                    ),
                },
                "status": {
                    "type": "string",
                    "enum": ["COMPLETED", "FAILED"],
                    "description": "Target status (default: COMPLETED)",
                },
            },
        },
    },
    "claim_execution": {
        "description": "Transition QUEUED -> CLAIMED and bind executor_id",
        "handler": handle_claim_execution,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {
                    "type": "string",
                    "description": "ID of the agent claiming this execution",
                },
            },
        },
    },
    "start_execution": {
        "description": "Transition CLAIMED -> RUNNING (enforces target locking)",
        "handler": handle_start_execution,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {"type": "string"},
            },
        },
    },
    "complete_execution": {
        "description": "Transition RUNNING -> COMPLETED and attach results",
        "handler": handle_complete_execution,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {"type": "string"},
                "result": {
                    "type": "string",
                    "description": "Execution output / observations",
                },
                "interpretation": {
                    "type": "string",
                    "description": (
                        "Natural-language analysis of the result the calling LLM produced "
                        "after reviewing the raw output. Markdown is supported. "
                        "Surfaced in the dashboard above the raw observations. "
                        "Voice: pentester drafting working notes — plain and concrete, "
                        "cite the URL/header/parameter/payload that proves the claim instead "
                        "of abstract risk language. No scaremongering, no marketing tone. "
                        "Length follows the observation; a few sentences is often enough. "
                        "Full tone contract in policies/note_taking_template.md."
                    ),
                },
            },
        },
    },
    "fail_execution": {
        "description": "Transition RUNNING -> FAILED and attach error info",
        "handler": handle_fail_execution,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {"type": "string"},
                "error_info": {
                    "type": "string",
                    "description": "Error description or traceback",
                },
                "interpretation": {
                    "type": "string",
                    "description": (
                        "Natural-language analysis of why the execution failed. "
                        "Markdown is supported. Surfaced in the dashboard above raw errors. "
                        "Voice: pentester drafting working notes — plain and concrete, "
                        "name the failing command/URL/parameter, no scaremongering, no "
                        "marketing tone. A couple of sentences is usually enough. "
                        "Full tone contract in policies/note_taking_template.md."
                    ),
                },
            },
        },
    },
    "list_queued_executions": {
        "description": "List all executions in QUEUED status",
        "handler": handle_list_queued_executions,
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Optional target filter",
                },
            },
        },
    },
    "cleanup_agents": {
        "description": "Stop and remove one or more agent containers by target, ID, or state",
        "handler": handle_cleanup_agents,
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Cleanup agents assigned to this target",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Cleanup a specific agent by name",
                },
                "all": {
                    "type": "boolean",
                    "description": "Cleanup all kali-agent containers",
                },
                "state": {
                    "type": "string",
                    "enum": ["running", "stopped"],
                    "description": "Filter by container state",
                },
            },
        },
    },
    "recover_execution": {
        "description": (
            "Recover stuck executions. Provide execution_id for single recovery, "
            "or set recover_stale=true to bulk-fail executions stuck longer than "
            "timeout_minutes (default 30)."
        ),
        "handler": handle_recover_execution,
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "Specific execution to recover",
                },
                "recover_stale": {
                    "type": "boolean",
                    "description": "Bulk-recover all stale executions",
                },
                "timeout_minutes": {
                    "type": "integer",
                    "description": "Staleness threshold in minutes (default: 30)",
                },
                "reason": {
                    "type": "string",
                    "description": "Recovery reason for audit log",
                },
            },
        },
    },
    "wait_for_completion": {
        "description": (
            "Block until an execution reaches COMPLETED or FAILED (or timeout). "
            "Eliminates polling — call once, get the result when ready. Use this "
            "after the execution has been queued and a compatible worker has been "
            "spawned or explicitly verified as already running."
        ),
        "handler": handle_wait_for_completion,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id"],
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "The execution ID to wait on",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Max seconds to wait (default: 600 = 10 min)",
                },
            },
        },
    },
    "create_reporting_engagement": {
        "description": (
            "Create a first-class reporting engagement in Taskmaster. Use this as "
            "the root container for client-facing findings and reports."
        ),
        "handler": handle_create_reporting_engagement,
        "inputSchema": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "engagement_id": {"type": "string"},
                "name": {"type": "string"},
                "slug": {"type": "string"},
                "client_name": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["active", "archived", "complete"],
                    "default": "active",
                },
                "summary": {"type": "string"},
            },
        },
    },
    "list_reporting_engagements": {
        "description": "List Taskmaster reporting engagements.",
        "handler": handle_list_reporting_engagements,
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "archived", "complete"],
                },
            },
        },
    },
    "create_reporting_finding": {
        "description": (
            "Promote a validated observation into Taskmaster's canonical reporting "
            "database. This is the source of truth for reports; do not use pwndoc "
            "fields or IDs."
        ),
        "handler": handle_create_reporting_finding,
        "inputSchema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "finding_id": {"type": "string"},
                "engagement_id": {"type": "string"},
                "title": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["Critical", "High", "Medium", "Low", "Info"],
                    "default": "Info",
                },
                "category": {
                    "type": "string",
                    "enum": FINDING_CATEGORY_ORDER,
                    "default": "TBD",
                    "description": (
                        "Finding category from the fixed internal set (mirrored from "
                        "pwndoc). Pick the best fit; use 'TBD' if not yet categorized. "
                        "An off-list value is coerced to 'Other'."
                    ),
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "draft",
                        "needs_review",
                        "confirmed",
                        "reported",
                        "accepted_risk",
                        "false_positive",
                    ],
                    "default": "draft",
                },
                "affected": {"type": "string"},
                "affected_assets": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "description": {"type": "string"},
                "impact": {"type": "string"},
                "proof_of_concept": {"type": "string"},
                "remediation": {"type": "string"},
                "cvss": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "string"},
                        "vector": {"type": "string"},
                    },
                },
                "cvss_score": {"type": "string"},
                "cvss_vector": {"type": "string"},
                "references": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "url": {"type": "string"},
                                },
                                "required": ["url"],
                            },
                        ]
                    },
                },
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string"},
                            "title": {"type": "string"},
                            "body": {"type": "string"},
                            "artifact_path": {"type": "string"},
                            "url": {"type": "string"},
                            "source_execution_id": {"type": "string"},
                        },
                    },
                },
                "source_execution_id": {"type": "string"},
                "created_by": {"type": "string"},
            },
        },
    },
    "get_reporting_finding": {
        "description": (
            "Fetch one canonical Taskmaster reporting finding, including evidence, "
            "references, and the dict shape expected by the docx renderer."
        ),
        "handler": handle_get_reporting_finding,
        "inputSchema": {
            "type": "object",
            "required": ["finding_id"],
            "properties": {"finding_id": {"type": "string"}},
        },
    },
    "update_reporting_finding": {
        "description": (
            "Update scalar fields on a canonical Taskmaster reporting finding. "
            "Use add_reporting_finding_evidence and add_reporting_finding_reference "
            "for proof material so edits do not silently replace the evidence trail."
        ),
        "handler": handle_update_reporting_finding,
        "inputSchema": {
            "type": "object",
            "required": ["finding_id"],
            "properties": {
                "finding_id": {"type": "string"},
                "engagement_id": {"type": "string"},
                "title": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["Critical", "High", "Medium", "Low", "Info"],
                },
                "category": {
                    "type": "string",
                    "enum": FINDING_CATEGORY_ORDER,
                    "description": (
                        "Finding category from the fixed internal set. An off-list "
                        "value is coerced to 'Other'."
                    ),
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "draft",
                        "needs_review",
                        "confirmed",
                        "reported",
                        "accepted_risk",
                        "false_positive",
                    ],
                },
                "affected": {"type": "string"},
                "description": {"type": "string"},
                "impact": {"type": "string"},
                "proof_of_concept": {"type": "string"},
                "remediation": {"type": "string"},
                "cvss_score": {"type": "string"},
                "cvss_vector": {"type": "string"},
                "source_execution_id": {"type": "string"},
                "updated_by": {"type": "string"},
            },
        },
    },
    "add_reporting_finding_evidence": {
        "description": "Attach evidence to a canonical Taskmaster reporting finding.",
        "handler": handle_add_reporting_finding_evidence,
        "inputSchema": {
            "type": "object",
            "required": ["finding_id"],
            "properties": {
                "finding_id": {"type": "string"},
                "kind": {"type": "string", "default": "note"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "artifact_path": {"type": "string"},
                "url": {"type": "string"},
                "source_execution_id": {"type": "string"},
                "created_by": {"type": "string"},
                "sort_order": {"type": "integer"},
            },
        },
    },
    "add_reporting_finding_reference": {
        "description": "Attach an external reference URL to a canonical Taskmaster finding.",
        "handler": handle_add_reporting_finding_reference,
        "inputSchema": {
            "type": "object",
            "required": ["finding_id", "url"],
            "properties": {
                "finding_id": {"type": "string"},
                "label": {"type": "string"},
                "url": {"type": "string"},
                "sort_order": {"type": "integer"},
            },
        },
    },
    "list_reporting_findings": {
        "description": (
            "List canonical Taskmaster reporting findings. Returns stored findings "
            "and report-shaped dicts ready for the existing docx renderer."
        ),
        "handler": handle_list_reporting_findings,
        "inputSchema": {
            "type": "object",
            "properties": {
                "engagement_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": [
                        "draft",
                        "needs_review",
                        "confirmed",
                        "reported",
                        "accepted_risk",
                        "false_positive",
                    ],
                },
                "include_evidence": {"type": "boolean", "default": True},
            },
        },
    },
    "request_reporting_docx": {
        "description": (
            "Queue a reporting executor task that renders stored Taskmaster "
            "findings through reporting.FindingDocxReport. This replaces manual "
            "JSON copying from the reporting database into report_skill arguments."
        ),
        "handler": handle_request_reporting_docx,
        "inputSchema": {
            "type": "object",
            "properties": {
                "engagement_id": {
                    "type": "string",
                    "description": "Render all findings for this engagement.",
                },
                "finding_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Render these specific findings, in this order.",
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "draft",
                        "needs_review",
                        "confirmed",
                        "reported",
                        "accepted_risk",
                        "false_positive",
                    ],
                    "description": "Optional status filter when engagement_id is used.",
                },
                "target": {
                    "type": "string",
                    "description": "Override the queued execution target label.",
                },
                "template_path": {
                    "type": "string",
                    "description": "Optional template override passed to the report skill.",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Optional output directory passed to the report skill.",
                },
            },
        },
    },
    "assemble_threat_model_context": {
        "description": (
            "Gather the engagement-scoped evidence for building an evidence-grounded "
            "threat model: scoped assets, recon/enumeration observations (executions "
            "tagged to the engagement), curated findings, existing models, and any "
            "unresolved assumptions/open questions. Combine with the engagement's "
            "Findings.md / recon-data.md (in your working directory) and write the model "
            "with create_threat_model + add_threat_model_entry; export with "
            "export_threat_model_markdown."
        ),
        "handler": handle_assemble_threat_model_context,
        "inputSchema": {
            "type": "object",
            "required": ["engagement_id"],
            "properties": {"engagement_id": {"type": "string"}},
        },
    },
    "create_threat_model": {
        "description": (
            "Create an evidence-grounded threat model for an engagement (a shell). Add "
            "entities (assumptions, roles, assets, attack paths, …) with "
            "add_threat_model_entry."
        ),
        "handler": handle_create_threat_model,
        "inputSchema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "threat_model_id": {"type": "string"},
                "engagement_id": {"type": "string"},
                "title": {"type": "string"},
                "methodology": {"type": "string", "default": "STRIDE"},
                "status": {
                    "type": "string",
                    "enum": ["draft", "in_review", "final"],
                    "default": "draft",
                },
                "review_date": {"type": "string", "description": "e.g. 2026-07-15"},
                "scope": {
                    "type": "string",
                    "description": "What the model covers (prose intro).",
                },
                "out_of_scope": {
                    "type": "string",
                    "description": "Explicitly excluded items (prose).",
                },
                "summary": {"type": "string"},
                "created_by": {"type": "string"},
            },
        },
    },
    "list_threat_models": {
        "description": "List threat models (with per-entity counts), filtered by engagement or status.",
        "handler": handle_list_threat_models,
        "inputSchema": {
            "type": "object",
            "properties": {
                "engagement_id": {"type": "string"},
                "status": {"type": "string", "enum": ["draft", "in_review", "final"]},
            },
        },
    },
    "get_threat_model": {
        "description": "Get a threat model with all entities grouped by type.",
        "handler": handle_get_threat_model,
        "inputSchema": {
            "type": "object",
            "required": ["threat_model_id"],
            "properties": {"threat_model_id": {"type": "string"}},
        },
    },
    "update_threat_model": {
        "description": (
            "Update the threat model shell (title, status draft→in_review→final, scope, "
            "out_of_scope, review_date, summary)."
        ),
        "handler": handle_update_threat_model,
        "inputSchema": {
            "type": "object",
            "required": ["threat_model_id"],
            "properties": {
                "threat_model_id": {"type": "string"},
                "engagement_id": {"type": "string"},
                "title": {"type": "string"},
                "methodology": {"type": "string"},
                "status": {"type": "string", "enum": ["draft", "in_review", "final"]},
                "review_date": {"type": "string"},
                "scope": {"type": "string"},
                "out_of_scope": {"type": "string"},
                "summary": {"type": "string"},
                "updated_by": {"type": "string"},
            },
        },
    },
    "add_threat_model_entry": {
        "description": (
            "Add one entity to a threat model. `entity_type` selects the section and its "
            "`fields`. `ref` (e.g. AP-1) is auto-generated if omitted; supply explicit "
            "refs so cross-references stay stable. Cross-references are ref strings you "
            "author (e.g. an attack_path's impacted_assets='CA-1, CA-4'). Tag evidence "
            "EVIDENCED / USER-CONFIRMED / ASSUMED / OUT-OF-SCOPE. Fields per entity_type: "
            "assumption{status,context,impact}; role{name,description}; "
            "asset{name,description}; terminal_goal{name,description}; "
            "attack_surface{name,description}; "
            "trust_boundary{boundary,protocol,authn,authz,encryption,validation,evidence}; "
            "attack_path{title,description,threat_category,impacted_assets,abused_surface,"
            "preconditions,existing_controls,gaps,likelihood,impact,priority,evidence,"
            "source_execution_id,finding_id}; "
            "test_objective{attack_path_ref,status,objective,priority,environment,notes}; "
            "existing_mitigation{mitigation,control_type,evidence,related_paths}; "
            "recommended_mitigation{recommendation,control_type,location,related_paths}; "
            "open_question{status,question,resolution}; evidence_note{note,status}."
        ),
        "handler": handle_add_threat_model_entry,
        "inputSchema": {
            "type": "object",
            "required": ["threat_model_id", "entity_type", "fields"],
            "properties": {
                "threat_model_id": {"type": "string"},
                "entity_type": {
                    "type": "string",
                    "enum": [
                        "assumption",
                        "role",
                        "asset",
                        "terminal_goal",
                        "attack_surface",
                        "trust_boundary",
                        "attack_path",
                        "test_objective",
                        "existing_mitigation",
                        "recommended_mitigation",
                        "open_question",
                        "evidence_note",
                    ],
                },
                "ref": {"type": "string", "description": "Optional explicit ref (e.g. AP-1)."},
                "fields": {"type": "object", "additionalProperties": True},
                "created_by": {"type": "string"},
            },
        },
    },
    "update_threat_model_entry": {
        "description": (
            "Update fields on one threat model entity, identified by entity_type + ref. "
            "Use this to propagate a validated answer into an attack path's likelihood/"
            "impact/priority/controls, or to resolve an open question. Same per-entity "
            "fields as add_threat_model_entry."
        ),
        "handler": handle_update_threat_model_entry,
        "inputSchema": {
            "type": "object",
            "required": ["threat_model_id", "entity_type", "ref", "fields"],
            "properties": {
                "threat_model_id": {"type": "string"},
                "entity_type": {"type": "string"},
                "ref": {"type": "string"},
                "fields": {"type": "object", "additionalProperties": True},
                "updated_by": {"type": "string"},
            },
        },
    },
    "delete_threat_model_entry": {
        "description": "Remove one threat model entity by entity_type + ref.",
        "handler": handle_delete_threat_model_entry,
        "inputSchema": {
            "type": "object",
            "required": ["threat_model_id", "entity_type", "ref"],
            "properties": {
                "threat_model_id": {"type": "string"},
                "entity_type": {"type": "string"},
                "ref": {"type": "string"},
            },
        },
    },
    "export_threat_model_markdown": {
        "description": (
            "Render a threat model as the reference-format markdown deliverable (summary "
            "tables first, then detailed attack paths). Returns the markdown and a "
            "suggested filename; save it in the engagement directory as "
            "<name>-threat-model.md."
        ),
        "handler": handle_export_threat_model_markdown,
        "inputSchema": {
            "type": "object",
            "required": ["threat_model_id"],
            "properties": {"threat_model_id": {"type": "string"}},
        },
    },
}


def _get_input_schema(tool):
    """Return the inputSchema for a tool, checking schema file then inline then default."""
    if tool.get("schema") and "inputSchema" in tool["schema"]:
        return tool["schema"]["inputSchema"]
    if tool.get("inputSchema"):
        return tool["inputSchema"]
    return {"type": "object", "properties": {}}


def dispatch(message):
    """Dispatch a parsed JSON message and return a response dict.

    Handles both JSON-RPC 2.0 (MCP protocol) and legacy message formats.
    Returns None for notifications that require no response.
    """
    # Handle JSON-RPC 2.0 format (MCP protocol)
    if "jsonrpc" in message and message.get("jsonrpc") == "2.0":
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})

        logging.info(f"JSON-RPC method: {method}, id: {msg_id}")

        # Handle notifications (no id = no response expected)
        if msg_id is None:
            if method and method.startswith("notifications/"):
                logging.info(f"Received notification: {method} (no response needed)")
            else:
                logging.warning(f"Received JSON-RPC message without id: {method}")
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "taskmaster", "version": "0.2.0"},
                    "capabilities": {"tools": {}},
                    "instructions": core_instructions(),
                },
            }

        elif method == "tools/list":
            tools_list = []
            for name, tool in TOOLS.items():
                tools_list.append(
                    {
                        "name": name,
                        "description": tool["description"],
                        "inputSchema": _get_input_schema(tool),
                    }
                )
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools_list},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if tool_name not in TOOLS:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }
            try:
                result = TOOLS[tool_name]["handler"](arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
                }
            except Exception as e:
                logging.error(f"Tool execution error: {e}", exc_info=True)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": f"Tool execution failed: {str(e)}"},
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    # Handle legacy format (for backwards compatibility with tests)
    if message.get("type") == "initialize":
        tools_list = []
        for name, tool in TOOLS.items():
            tool_def = {"name": name, "description": tool["description"]}
            schema = _get_input_schema(tool)
            if schema.get("properties"):
                tool_def["inputSchema"] = schema
            tools_list.append(tool_def)

        return {
            "type": "initialize_response",
            "protocolVersion": "1.0.0",
            "serverInfo": {"name": "taskmaster", "version": "0.2.0"},
            "capabilities": {"tools": {}},
            "instructions": core_instructions(),
            "tools": tools_list,
        }

    if message.get("type") == "tool_call":
        tool_name = message.get("tool")
        payload = message.get("arguments", {})

        if tool_name not in TOOLS:
            return {"error": f"Unknown tool: {tool_name}"}

        result = TOOLS[tool_name]["handler"](payload)
        return {"type": "tool_result", "tool": tool_name, "result": result}

    return {"error": "Unknown message type"}


# ---------------------------------------------------------------------------
# HTTP mode — MCP JSON-RPC endpoint (dashboard lives in dashboard/webapp.py)
# ---------------------------------------------------------------------------


class MCPHandler(BaseHTTPRequestHandler):
    """Handle MCP JSON-RPC over HTTP (POST) plus a liveness probe.

    The dashboard is served by a separate listener (see ``run_http``) so it can
    bind a loopback-only interface while this endpoint stays reachable by agent
    containers.
    """

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            message = json.loads(body)
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json(400, {"error": f"Invalid JSON: {e}"})
            return

        logging.debug(f"HTTP received: {message}")
        response = dispatch(message)
        if response is None:
            # Notification — no response body expected.
            self.send_response(204)
            self.end_headers()
        else:
            self._send_json(200, response)

    def _send_json(self, status, data):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        """Route http.server logs through the logging module."""
        logging.info(format % args)


def run_http(host, port, dashboard_host, dashboard_port):
    """Start the MCP endpoint and the dashboard on separate listeners.

    The MCP server binds ``host`` (default 0.0.0.0) so agent containers can
    reach it via host.docker.internal. The dashboard binds ``dashboard_host``
    (default 127.0.0.1) so it is not exposed beyond the local machine. Both shut
    down gracefully on SIGTERM (how Docker/systemd stop the process) and SIGINT.
    """
    from dashboard.webapp import DashboardHandler

    mcp_server = ThreadingHTTPServer((host, port), MCPHandler)
    dash_server = ThreadingHTTPServer((dashboard_host, dashboard_port), DashboardHandler)

    logging.info("Taskmaster MCP endpoint listening on %s:%s", host, port)
    logging.info("Taskmaster dashboard listening on %s:%s", dashboard_host, dashboard_port)
    print(f"Taskmaster MCP endpoint listening on {host}:{port}", file=sys.stderr)
    print(
        f"Taskmaster dashboard listening on http://{dashboard_host}:{dashboard_port}",
        file=sys.stderr,
    )

    dash_thread = threading.Thread(
        target=dash_server.serve_forever, name="taskmaster-dashboard", daemon=True
    )
    dash_thread.start()

    def _shutdown(signum, _frame):
        # serve_forever() runs in this (main) thread and shutdown() blocks until
        # it returns, so each shutdown must run on its own thread.
        logging.info("Received signal %s — shutting down", signum)
        threading.Thread(target=mcp_server.shutdown, daemon=True).start()
        threading.Thread(target=dash_server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        mcp_server.serve_forever()
    finally:
        mcp_server.server_close()
        dash_server.server_close()
        logging.info("HTTP servers stopped")


# ---------------------------------------------------------------------------
# STDIO mode — original line-based JSON protocol
# ---------------------------------------------------------------------------


def _send_stdio(response):
    output = json.dumps(response) + "\n"
    logging.debug(f"Sending: {output.strip()}")
    sys.stdout.write(output)
    sys.stdout.flush()


def run_stdio():
    """Run the server in STDIO mode (MCP transport)."""
    logging.info("Taskmaster MCP server starting (STDIO mode)...")

    for line in sys.stdin:
        logging.debug(f"Received: {line.strip()}")

        try:
            message = json.loads(line)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            _send_stdio({"error": "Invalid JSON"})
            continue

        logging.debug(f"Parsed message: {message}")

        response = dispatch(message)
        if response is not None:
            _send_stdio(response)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Taskmaster MCP Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run as a persistent HTTP server instead of STDIO",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("TASKMASTER_HOST", "0.0.0.0"),
        help="HTTP server bind address (default: $TASKMASTER_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("TASKMASTER_PORT", "5000")),
        help="MCP endpoint port (default: $TASKMASTER_PORT or 5000)",
    )
    parser.add_argument(
        "--dashboard-host",
        default=os.environ.get("TASKMASTER_DASHBOARD_HOST", "127.0.0.1"),
        help=(
            "Dashboard bind address (default: $TASKMASTER_DASHBOARD_HOST or "
            "127.0.0.1 — loopback only, not exposed beyond this machine)"
        ),
    )
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=int(os.environ.get("TASKMASTER_DASHBOARD_PORT", "5001")),
        help="Dashboard port (default: $TASKMASTER_DASHBOARD_PORT or 5001)",
    )
    args = parser.parse_args()

    start_reaper_thread()

    if args.http:
        run_http(args.host, args.port, args.dashboard_host, args.dashboard_port)
    else:
        run_stdio()


if __name__ == "__main__":
    main()

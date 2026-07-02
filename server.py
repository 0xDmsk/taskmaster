import argparse
import json
import logging
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import config
from tools.request_security_action import handle_request
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
            "Request execution of a security-related action. Commands are validated "
            "against macOS VM platform constraints — raw-socket scans (nmap -sS, -sU, "
            "-O) are blocked. Use nmap -sT. This tool only queues work; after it "
            "returns QUEUED, spawn or reuse a compatible agent, then monitor with "
            "wait_for_completion."
        ),
        "handler": handle_request,
        "schema": load_tool_schema("request_security_action"),
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
                    "enum": ["kali", "playwright", "reporting"],
                    "description": (
                        "Executor type to launch. Use 'kali' for CLI/python tasks, "
                        "'playwright' for browser-rendered tasks, or 'reporting' "
                        "for rendering client-facing deliverables via 'report_skill' "
                        "actions (e.g. reporting.FindingDocxReport)."
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
                "category": {"type": "string", "default": "General"},
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
                "category": {"type": "string"},
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
# HTTP mode — persistent server using stdlib http.server
# ---------------------------------------------------------------------------


class TaskmasterHTTPHandler(BaseHTTPRequestHandler):
    """Handle POST /mcp and GET /dashboard requests."""

    # Lazy imports to avoid circular deps and startup cost when dashboard isn't used
    _dashboard_imported = False

    @classmethod
    def _ensure_dashboard(cls):
        if not cls._dashboard_imported:
            import dashboard
            import dashboard.api as dash_api
            import dashboard.agents as dash_agents

            cls._dashboard = dashboard
            cls._dash_api = dash_api
            cls._dash_agents = dash_agents
            cls._dashboard_imported = True

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/executions"
        qs = parse_qs(parsed.query)
        # Flatten query params (take first value)
        params = {k: v[0] for k, v in qs.items()}

        self._ensure_dashboard()
        api = self._dash_api
        agents_mod = self._dash_agents
        render = self._dashboard.render

        is_htmx = self.headers.get("HX-Request") == "true"

        # --- Static files ---
        if path.startswith("/static/"):
            self._serve_static(path)
            return

        # --- API endpoints ---
        if path == "/api/stats":
            data = api.get_stats()
            if is_htmx:
                html = render("partials/stats_bar.html", stats=data)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        if path == "/api/executions":
            data = api.get_executions(
                status=params.get("status"),
                target=params.get("target"),
                phase=params.get("phase"),
            )
            if is_htmx:
                html = render("partials/execution_table.html", executions=data)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        # Detail endpoint must come before the generic /api/executions/<id>
        if path.endswith("/detail") and path.startswith("/api/executions/"):
            eid = path.split("/api/executions/", 1)[1].replace("/detail", "")
            data = api.get_execution_detail(eid)
            if data is None:
                self._send_json(404, {"error": "Not found"})
            elif is_htmx:
                html = render("partials/execution_detail.html", e=data)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        if path.startswith("/api/executions/"):
            eid = path.split("/api/executions/", 1)[1]
            data = api.get_execution(eid)
            if data is None:
                self._send_json(404, {"error": "Not found"})
            else:
                self._send_json(200, data)
            return

        if path.endswith("/detail") and path.startswith("/api/targets/"):
            target = path.split("/api/targets/", 1)[1].replace("/detail", "")
            data = api.get_target_detail(target)
            if data is None:
                self._send_json(404, {"error": "Not found"})
            elif is_htmx:
                html = render("partials/target_detail.html", detail=data)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        if path == "/api/targets":
            data = api.get_targets()
            if is_htmx:
                phases = api.PHASES
                html = render("partials/target_cards.html", targets=data, phases=phases)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        if path.endswith("/detail") and path.startswith("/api/agents/"):
            executor_id = path.split("/api/agents/", 1)[1].replace("/detail", "")
            history = agents_mod.get_agent_history()
            agent = next((a for a in history if a["executor_id"] == executor_id), None)
            if agent is None:
                self._send_json(404, {"error": "Not found"})
            elif is_htmx:
                html = render("partials/agent_detail.html", agent=agent)
                self._send_html(200, html)
            else:
                self._send_json(200, agent)
            return

        if path == "/api/agents/history":
            data = agents_mod.get_agent_history()
            if is_htmx:
                html = render("partials/agent_list.html", agents=data)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        if path == "/api/agents":
            data = agents_mod.get_agents()
            if is_htmx:
                html = render("partials/agent_list.html", agents=data)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        if path in ("/api/observations", "/api/findings"):
            data = api.get_observations()
            if is_htmx:
                html = render("partials/observations_detail.html", observations=data)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        if path == "/api/reporting/findings":
            data = api.get_report_findings(
                engagement_id=params.get("engagement_id"),
                status=params.get("status"),
                severity=params.get("severity"),
                query=params.get("q"),
            )
            if is_htmx:
                html = render("partials/report_findings_list.html", findings=data)
                self._send_html(200, html)
            else:
                self._send_json(200, data)
            return

        # --- Dashboard pages ---
        stats = api.get_stats()

        if path in ("/", "/executions"):
            execs = api.get_executions(
                status=params.get("status"),
                target=params.get("target"),
                phase=params.get("phase"),
            )
            html = render(
                "executions.html",
                page="executions",
                stats=stats,
                executions=execs,
                filters=params,
            )
            self._send_html(200, html)
            return

        if path == "/targets":
            targets = api.get_targets()
            html = render(
                "targets.html",
                page="targets",
                stats=stats,
                targets=targets,
                phases=api.PHASES,
            )
            self._send_html(200, html)
            return

        if path == "/findings":
            self.send_response(302)
            self.send_header("Location", "/observations")
            self.end_headers()
            return

        if path == "/observations":
            observations = api.get_observations()
            html = render(
                "observations.html",
                page="observations",
                stats=stats,
                observations=observations,
            )
            self._send_html(200, html)
            return

        if path == "/reporting/findings":
            filters = {
                "engagement_id": params.get("engagement_id"),
                "status": params.get("status"),
                "severity": params.get("severity"),
                "q": params.get("q"),
            }
            findings = api.get_report_findings(
                engagement_id=filters["engagement_id"],
                status=filters["status"],
                severity=filters["severity"],
                query=filters["q"],
            )
            html = render(
                "report_findings.html",
                page="report_findings",
                stats=stats,
                findings=findings,
                options=api.get_report_finding_options(),
                filters=filters,
                message=params.get("message"),
                error=params.get("error"),
            )
            self._send_html(200, html)
            return

        if path == "/reporting/findings/new":
            html = render(
                "report_finding_form.html",
                page="report_findings",
                stats=stats,
                mode="new",
                finding=None,
                options=api.get_report_finding_options(),
                message=params.get("message"),
                error=params.get("error"),
            )
            self._send_html(200, html)
            return

        if path.endswith("/edit") and path.startswith("/reporting/findings/"):
            finding_id = path.split("/reporting/findings/", 1)[1].replace("/edit", "")
            finding = api.get_report_finding_detail(finding_id)
            if not finding:
                self._send_html(404, "<h1>Finding not found</h1>")
                return
            html = render(
                "report_finding_form.html",
                page="report_findings",
                stats=stats,
                mode="edit",
                finding=finding,
                options=api.get_report_finding_options(),
                message=params.get("message"),
                error=params.get("error"),
            )
            self._send_html(200, html)
            return

        if path == "/agents":
            agent_list = agents_mod.get_agent_history()
            html = render(
                "agents.html",
                page="agents",
                stats=stats,
                agents=agent_list,
            )
            self._send_html(200, html)
            return

        self._send_html(404, "<h1>404 Not Found</h1>")

    def _serve_static(self, path):
        """Serve files from dashboard/static/."""
        static_dir = os.path.join(config.PROJECT_DIR, "dashboard", "static")
        filename = path.replace("/static/", "", 1)
        filepath = os.path.normpath(os.path.join(static_dir, filename))
        # Prevent path traversal
        if not filepath.startswith(static_dir):
            self._send_html(403, "Forbidden")
            return
        if not os.path.isfile(filepath):
            self._send_html(404, "Not found")
            return
        content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, status, html):
        payload = html.encode() if isinstance(html, str) else html
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if path.startswith("/reporting/"):
            form = self._parse_form(body)
            self._handle_reporting_post(path, form)
            return

        try:
            message = json.loads(body)
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json(400, {"error": f"Invalid JSON: {e}"})
            return

        logging.debug(f"HTTP received: {message}")
        response = dispatch(message)

        if response is None:
            # Notification — no response body expected, send 204
            self.send_response(204)
            self.end_headers()
        else:
            self._send_json(200, response)

    def _parse_form(self, body):
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        form = {}
        for key, values in parsed.items():
            form[key] = values if len(values) > 1 else values[0]
        return form

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def _redirect_with_message(self, location, *, message=None, error=None):
        if not location.startswith("/"):
            location = "/reporting/findings"
        params = {}
        if message:
            params["message"] = message
        if error:
            params["error"] = error
        if params:
            separator = "&" if "?" in location else "?"
            location = f"{location}{separator}{urlencode(params)}"
        self._redirect(location)

    @staticmethod
    def _blank_to_none(value):
        if isinstance(value, list):
            value = value[0] if value else ""
        return value if value != "" else None

    def _finding_payload_from_form(self, form):
        return {
            "engagement_id": self._blank_to_none(form.get("engagement_id")),
            "title": form.get("title", ""),
            "severity": form.get("severity", "Info"),
            "category": form.get("category", "General"),
            "status": form.get("status", "draft"),
            "affected": form.get("affected", ""),
            "description": form.get("description", ""),
            "impact": form.get("impact", ""),
            "proof_of_concept": form.get("proof_of_concept", ""),
            "remediation": form.get("remediation", ""),
            "cvss_score": self._blank_to_none(form.get("cvss_score")),
            "cvss_vector": self._blank_to_none(form.get("cvss_vector")),
            "source_execution_id": self._blank_to_none(form.get("source_execution_id")),
        }

    def _handle_reporting_post(self, path, form):
        if path == "/reporting/engagements":
            result = handle_create_reporting_engagement(
                {
                    "name": form.get("name", ""),
                    "client_name": self._blank_to_none(form.get("client_name")),
                    "summary": self._blank_to_none(form.get("summary")),
                }
            )
            if "error" in result:
                self._redirect_with_message(
                    self.headers.get("Referer", "/reporting/findings"),
                    error=result["error"],
                )
            else:
                self._redirect_with_message(
                    self.headers.get("Referer", "/reporting/findings"),
                    message="Engagement created",
                )
            return

        if path == "/reporting/findings":
            payload = self._finding_payload_from_form(form)
            payload["created_by"] = "dashboard"
            result = handle_create_reporting_finding(payload)
            if "error" in result:
                self._redirect_with_message("/reporting/findings/new", error=result["error"])
            else:
                finding_id = result["finding"]["finding_id"]
                self._redirect_with_message(
                    f"/reporting/findings/{finding_id}/edit",
                    message="Finding created",
                )
            return

        if path == "/reporting/reports/docx":
            finding_id = self._blank_to_none(form.get("finding_id"))
            args = {
                "engagement_id": self._blank_to_none(form.get("engagement_id")),
                "status": self._blank_to_none(form.get("status")),
                "target": self._blank_to_none(form.get("target")),
            }
            if finding_id:
                args["finding_ids"] = [finding_id]
                args.pop("engagement_id", None)
                args.pop("status", None)
            result = handle_request_reporting_docx(args)
            if "error" in result:
                self._redirect_with_message(
                    self.headers.get("Referer", "/reporting/findings"),
                    error=result["error"],
                )
            else:
                self._redirect(f"/executions#exec:{result['execution_id']}")
            return

        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "reporting" and parts[1] == "findings":
            finding_id = parts[2]
            if len(parts) == 3:
                payload = self._finding_payload_from_form(form)
                payload["finding_id"] = finding_id
                payload["updated_by"] = "dashboard"
                result = handle_update_reporting_finding(payload)
                if "error" in result:
                    self._redirect_with_message(
                        f"/reporting/findings/{finding_id}/edit",
                        error=result["error"],
                    )
                else:
                    self._redirect_with_message(
                        f"/reporting/findings/{finding_id}/edit",
                        message="Finding updated",
                    )
                return

            if len(parts) == 4 and parts[3] == "evidence":
                result = handle_add_reporting_finding_evidence(
                    {
                        "finding_id": finding_id,
                        "kind": form.get("kind", "note"),
                        "title": self._blank_to_none(form.get("title")),
                        "body": self._blank_to_none(form.get("body")),
                        "artifact_path": self._blank_to_none(form.get("artifact_path")),
                        "url": self._blank_to_none(form.get("url")),
                        "source_execution_id": self._blank_to_none(form.get("source_execution_id")),
                        "created_by": "dashboard",
                    }
                )
                if "error" in result:
                    self._redirect_with_message(
                        f"/reporting/findings/{finding_id}/edit",
                        error=result["error"],
                    )
                else:
                    self._redirect_with_message(
                        f"/reporting/findings/{finding_id}/edit",
                        message="Evidence added",
                    )
                return

            if len(parts) == 4 and parts[3] == "references":
                result = handle_add_reporting_finding_reference(
                    {
                        "finding_id": finding_id,
                        "label": self._blank_to_none(form.get("label")),
                        "url": form.get("url", ""),
                    }
                )
                if "error" in result:
                    self._redirect_with_message(
                        f"/reporting/findings/{finding_id}/edit",
                        error=result["error"],
                    )
                else:
                    self._redirect_with_message(
                        f"/reporting/findings/{finding_id}/edit",
                        message="Reference added",
                    )
                return

        self._send_html(404, "<h1>404 Not Found</h1>")

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


def run_http(host, port):
    """Start a persistent HTTP server."""
    server = ThreadingHTTPServer((host, port), TaskmasterHTTPHandler)
    logging.info(f"Taskmaster HTTP server listening on {host}:{port}")
    print(f"Taskmaster HTTP server listening on {host}:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down HTTP server")
        server.server_close()


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
        help="HTTP server port (default: $TASKMASTER_PORT or 5000)",
    )
    args = parser.parse_args()

    start_reaper_thread()

    if args.http:
        run_http(args.host, args.port)
    else:
        run_stdio()


if __name__ == "__main__":
    main()

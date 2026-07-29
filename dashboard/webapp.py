"""Dashboard web layer: a table-driven HTTP router and its request handler.

Split out of ``server.py`` so the dashboard can bind to a loopback-only
interface while the MCP JSON-RPC endpoint keeps binding an interface reachable
by agent containers (see ``server.run_http``). Keeping the routing here also
replaces the former ~360-line ``if path == ...`` chain with an explicit route
table, so adding or reordering a route is a one-line change.

Route handlers are methods on :class:`DashboardHandler`. GET handlers read
``self.params`` / ``self.is_htmx`` / ``self.scope`` (populated in ``do_GET``)
and take the captured path groups as their only argument. POST handlers read
``self.form`` and likewise take the captured path groups.
"""

import json
import logging
import mimetypes
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import config
import dashboard.agents as agents_mod
import dashboard.api as api
from dashboard import render
from state.reporting import (
    create_asset,
    create_finding,
    create_finding_template,
    delete_asset,
    delete_finding_template,
    finding_to_template_payload,
    get_finding,
    get_finding_template,
    get_threat_model,
    render_threat_model_markdown,
    template_to_finding_payload,
    update_finding_template,
)
from state.storage import update_execution
from tools.add_reporting_finding_evidence import handle_add_reporting_finding_evidence
from tools.add_reporting_finding_reference import handle_add_reporting_finding_reference
from tools.create_reporting_engagement import handle_create_reporting_engagement
from tools.create_reporting_finding import handle_create_reporting_finding
from tools.request_reporting_docx import handle_request_reporting_docx
from tools.update_reporting_finding import handle_update_reporting_finding

logger = logging.getLogger(__name__)


class Router:
    """Ordered (method, regex, handler-name) table with first-match dispatch.

    Patterns are matched with ``fullmatch`` against the normalized path. Named
    groups become the ``cap`` dict passed to the handler. Because ``[^/]+``
    segments never span a slash, more-specific routes disambiguate themselves;
    routes are still registered specific-first for readability.
    """

    def __init__(self):
        self._routes = []

    def add(self, method, pattern, handler_name):
        self._routes.append((method, re.compile(pattern), handler_name))
        return self

    def match(self, method, path):
        for route_method, pattern, handler_name in self._routes:
            if route_method != method:
                continue
            mo = pattern.fullmatch(path)
            if mo:
                return handler_name, mo.groupdict()
        return None, None


ROUTER = Router()

# --- GET routes -----------------------------------------------------------
ROUTER.add("GET", r"/static/(?P<rest>.*)", "serve_static")
ROUTER.add("GET", r"/reporting/download", "get_download")
ROUTER.add("GET", r"/reporting/threat-models/(?P<tm_id>[^/]+)/export", "get_threat_model_export")
ROUTER.add("GET", r"/api/stats", "api_stats")
ROUTER.add("GET", r"/api/executions", "api_executions")
ROUTER.add("GET", r"/api/executions/(?P<eid>[^/]+)/detail", "api_execution_detail")
ROUTER.add("GET", r"/api/executions/(?P<eid>[^/]+)", "api_execution")
# Target is passed as a query param (?target=), not a path segment: real targets
# are often URLs containing slashes, which a path segment can't hold.
ROUTER.add("GET", r"/api/targets/detail", "api_target_detail")
ROUTER.add("GET", r"/api/targets", "api_targets")
ROUTER.add("GET", r"/api/agents/(?P<executor_id>[^/]+)/detail", "api_agent_detail")
ROUTER.add("GET", r"/api/agents/history", "api_agents_history")
ROUTER.add("GET", r"/api/agents", "api_agents")
ROUTER.add("GET", r"/api/observations", "api_observations")
ROUTER.add("GET", r"/api/findings", "api_observations")
ROUTER.add("GET", r"/api/reporting/templates", "api_finding_templates")
ROUTER.add(
    "GET",
    r"/api/reporting/engagements/(?P<engagement_id>[^/]+)/findings",
    "api_engagement_findings",
)
ROUTER.add("GET", r"/overview", "page_overview")
ROUTER.add("GET", r"/executions", "page_executions")
ROUTER.add("GET", r"/targets", "page_targets")
ROUTER.add("GET", r"/findings", "redirect_observations")
ROUTER.add("GET", r"/observations", "page_observations")
ROUTER.add("GET", r"/reporting/engagements", "page_engagements")
ROUTER.add("GET", r"/reporting/engagements/(?P<engagement_id>[^/]+)", "page_engagement_workspace")
ROUTER.add("GET", r"/reporting/findings/new", "page_report_finding_new")
ROUTER.add("GET", r"/reporting/findings/(?P<finding_id>[^/]+)/edit", "page_report_finding_edit")
# The flat cross-engagement findings list is gone (findings live in engagements);
# the bare path redirects there. The finding create/edit form routes above stay.
ROUTER.add("GET", r"/reporting/findings", "redirect_engagements")
ROUTER.add("GET", r"/reporting/templates/new", "page_finding_template_new")
ROUTER.add("GET", r"/reporting/templates/(?P<template_id>[^/]+)/edit", "page_finding_template_edit")
ROUTER.add("GET", r"/reporting/templates", "page_finding_templates")
ROUTER.add("GET", r"/agents", "page_agents")

# --- POST routes ----------------------------------------------------------
ROUTER.add("POST", r"/reporting/engagements", "post_create_engagement")
ROUTER.add(
    "POST", r"/reporting/engagements/(?P<engagement_id>[^/]+)/assets", "post_add_asset"
)
ROUTER.add(
    "POST",
    r"/reporting/engagements/(?P<engagement_id>[^/]+)/assets/(?P<asset_id>[^/]+)/delete",
    "post_delete_asset",
)
ROUTER.add("POST", r"/reporting/reports/docx", "post_request_docx")
ROUTER.add("POST", r"/reporting/findings", "post_create_finding")
ROUTER.add("POST", r"/reporting/findings/(?P<finding_id>[^/]+)/status", "post_finding_status")
ROUTER.add("POST", r"/reporting/findings/(?P<finding_id>[^/]+)/evidence", "post_finding_evidence")
ROUTER.add(
    "POST", r"/reporting/findings/(?P<finding_id>[^/]+)/references", "post_finding_reference"
)
ROUTER.add(
    "POST",
    r"/reporting/findings/(?P<finding_id>[^/]+)/save-as-template",
    "post_finding_save_as_template",
)
ROUTER.add("POST", r"/reporting/findings/(?P<finding_id>[^/]+)", "post_update_finding")
ROUTER.add("POST", r"/reporting/templates", "post_create_template")
ROUTER.add("POST", r"/reporting/templates/(?P<template_id>[^/]+)/delete", "post_delete_template")
ROUTER.add("POST", r"/reporting/templates/(?P<template_id>[^/]+)/use", "post_use_template")
ROUTER.add("POST", r"/reporting/templates/(?P<template_id>[^/]+)", "post_update_template")
ROUTER.add("POST", r"/executions/(?P<execution_id>[^/]+)/engagement", "post_execution_engagement")


class DashboardHandler(BaseHTTPRequestHandler):
    """Serves the dashboard pages, htmx partials, JSON API, and reporting forms."""

    # ----------------------------------------------------------------- #
    # Dispatch                                                          #
    # ----------------------------------------------------------------- #

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/overview"
        self.params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        self.is_htmx = self.headers.get("HX-Request") == "true"

        if path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return

        self.scope = self._scope_id()
        name, cap = ROUTER.match("GET", path)
        if name is None:
            self._send_html(404, "<h1>404 Not Found</h1>")
            return
        getattr(self, name)(cap)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length", 0))
        self.form = self._parse_form(self.rfile.read(length))

        name, cap = ROUTER.match("POST", path)
        if name is None:
            self._send_html(404, "<h1>404 Not Found</h1>")
            return
        getattr(self, name)(cap)

    # ----------------------------------------------------------------- #
    # GET handlers                                                       #
    # ----------------------------------------------------------------- #

    def serve_static(self, cap):
        static_dir = os.path.join(config.PROJECT_DIR, "dashboard", "static")
        filepath = os.path.normpath(os.path.join(static_dir, cap["rest"]))
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

    def get_download(self, cap):
        try:
            index = int(self.params.get("i", "0"))
        except ValueError:
            index = -1
        host_path = api.get_render_artifact(self.params.get("exec", ""), index)
        if not host_path:
            self._send_html(404, "<h1>Artifact not found</h1>")
            return
        self._send_download(host_path)

    def get_threat_model_export(self, cap):
        tm_id = cap["tm_id"]
        model = get_threat_model(tm_id)
        if not model:
            self._send_html(404, "<h1>Threat model not found</h1>")
            return
        markdown = render_threat_model_markdown(tm_id) or ""
        slug = re.sub(r"[^a-z0-9]+", "-", (model.get("title") or "").lower()).strip("-")
        filename = f"{slug or 'threat-model'}-threat-model.md"
        payload = markdown.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def api_stats(self, cap):
        data = api.get_stats(engagement_id=self.scope)
        if self.is_htmx:
            self._send_html(200, render("partials/stats_bar.html", stats=data))
        else:
            self._send_json(200, data)

    def api_executions(self, cap):
        data = api.get_executions(
            status=self.params.get("status"),
            target=self.params.get("target"),
            phase=self.params.get("phase"),
            engagement_id=self.scope,
        )
        if self.is_htmx:
            self._send_html(200, render("partials/execution_table.html", executions=data))
        else:
            self._send_json(200, data)

    def api_execution_detail(self, cap):
        data = api.get_execution_detail(cap["eid"])
        if data is None:
            self._send_json(404, {"error": "Not found"})
        elif self.is_htmx:
            self._send_html(200, render("partials/execution_detail.html", e=data))
        else:
            self._send_json(200, data)

    def api_execution(self, cap):
        data = api.get_execution(cap["eid"])
        if data is None:
            self._send_json(404, {"error": "Not found"})
        else:
            self._send_json(200, data)

    def api_target_detail(self, cap):
        data = api.get_target_detail(self.params.get("target", ""))
        if data is None:
            self._send_json(404, {"error": "Not found"})
        elif self.is_htmx:
            self._send_html(200, render("partials/target_detail.html", detail=data))
        else:
            self._send_json(200, data)

    def api_targets(self, cap):
        data = api.get_targets(engagement_id=self.scope)
        if self.is_htmx:
            self._send_html(
                200, render("partials/target_cards.html", targets=data, phases=api.PHASES)
            )
        else:
            self._send_json(200, data)

    def api_agent_detail(self, cap):
        history = agents_mod.get_agent_history(engagement_id=self.scope)
        agent = next((a for a in history if a["executor_id"] == cap["executor_id"]), None)
        if agent is None:
            self._send_json(404, {"error": "Not found"})
        elif self.is_htmx:
            self._send_html(200, render("partials/agent_detail.html", agent=agent))
        else:
            self._send_json(200, agent)

    def api_agents_history(self, cap):
        data = agents_mod.get_agent_history(engagement_id=self.scope)
        if self.is_htmx:
            self._send_html(200, render("partials/agent_list.html", agents=data))
        else:
            self._send_json(200, data)

    def api_agents(self, cap):
        data = agents_mod.get_agents()
        if self.is_htmx:
            self._send_html(200, render("partials/agent_list.html", agents=data))
        else:
            self._send_json(200, data)

    def api_observations(self, cap):
        data = api.get_observations(engagement_id=self.scope)
        if self.is_htmx:
            self._send_html(200, render("partials/observations_detail.html", observations=data))
        else:
            self._send_json(200, data)

    def api_finding_templates(self, cap):
        data = api.get_finding_templates(
            severity=self.params.get("severity"),
            category=self.params.get("category"),
            query=self.params.get("q"),
        )
        if self.is_htmx:
            self._send_html(
                200,
                render(
                    "partials/finding_templates_list.html",
                    templates=data,
                    engagements=api.list_engagements(),
                ),
            )
        else:
            self._send_json(200, data)

    def api_engagement_findings(self, cap):
        engagement_id = cap["engagement_id"]
        findings = api.get_engagement_findings(
            engagement_id,
            status=self.params.get("status"),
            severity=self.params.get("severity"),
            query=self.params.get("q"),
        )
        if self.is_htmx:
            self._send_html(
                200,
                render(
                    "partials/engagement_findings_list.html",
                    findings=findings,
                    options=api.get_report_finding_options(),
                    engagement_id=engagement_id,
                ),
            )
        else:
            self._send_json(200, findings)

    def page_overview(self, cap):
        self._send_html(
            200,
            render(
                "overview.html",
                page="overview",
                stats=self._stats(),
                overview=api.get_overview(engagement_id=self.scope),
            ),
        )

    def page_executions(self, cap):
        execs = api.get_executions(
            status=self.params.get("status"),
            target=self.params.get("target"),
            phase=self.params.get("phase"),
            engagement_id=self.scope,
        )
        self._send_html(
            200,
            render(
                "executions.html",
                page="executions",
                stats=self._stats(),
                executions=execs,
                filters=self.params,
            ),
        )

    def page_targets(self, cap):
        self._send_html(
            200,
            render(
                "targets.html",
                page="targets",
                stats=self._stats(),
                targets=api.get_targets(engagement_id=self.scope),
                phases=api.PHASES,
            ),
        )

    def redirect_observations(self, cap):
        self.send_response(302)
        self.send_header("Location", "/observations")
        self.end_headers()

    def page_observations(self, cap):
        self._send_html(
            200,
            render(
                "observations.html",
                page="observations",
                stats=self._stats(),
                observations=api.get_observations(engagement_id=self.scope),
            ),
        )

    def page_engagements(self, cap):
        self._send_html(
            200,
            render(
                "engagements.html",
                page="engagements",
                stats=self._stats(),
                engagements=api.get_engagements_overview(),
                message=self.params.get("message"),
                error=self.params.get("error"),
            ),
        )

    def page_engagement_workspace(self, cap):
        engagement_id = cap["engagement_id"]
        filters = {
            "status": self.params.get("status"),
            "severity": self.params.get("severity"),
            "q": self.params.get("q"),
        }
        workspace = api.get_engagement_workspace(
            engagement_id,
            status=filters["status"],
            severity=filters["severity"],
            query=filters["q"],
        )
        if not workspace:
            self._send_html(404, "<h1>Engagement not found</h1>")
            return
        self._send_html(
            200,
            render(
                "engagement_workspace.html",
                page="engagements",
                stats=self._stats(),
                workspace=workspace,
                options=api.get_report_finding_options(),
                filters=filters,
                message=self.params.get("message"),
                error=self.params.get("error"),
            ),
        )

    def redirect_engagements(self, cap):
        self.send_response(302)
        self.send_header("Location", "/reporting/engagements")
        self.end_headers()

    def page_finding_templates(self, cap):
        filters = {
            "severity": self.params.get("severity"),
            "category": self.params.get("category"),
            "q": self.params.get("q"),
        }
        templates = api.get_finding_templates(
            severity=filters["severity"],
            category=filters["category"],
            query=filters["q"],
        )
        self._send_html(
            200,
            render(
                "finding_templates.html",
                page="finding_templates",
                stats=self._stats(),
                templates=templates,
                options=api.get_finding_template_options(),
                engagements=api.list_engagements(),
                filters=filters,
                message=self.params.get("message"),
                error=self.params.get("error"),
            ),
        )

    def page_finding_template_new(self, cap):
        self._send_html(
            200,
            render(
                "finding_template_form.html",
                page="finding_templates",
                stats=self._stats(),
                mode="new",
                template=None,
                options=api.get_finding_template_options(),
                message=self.params.get("message"),
                error=self.params.get("error"),
            ),
        )

    def page_finding_template_edit(self, cap):
        template = api.get_finding_template_detail(cap["template_id"])
        if not template:
            self._send_html(404, "<h1>Template not found</h1>")
            return
        self._send_html(
            200,
            render(
                "finding_template_form.html",
                page="finding_templates",
                stats=self._stats(),
                mode="edit",
                template=template,
                options=api.get_finding_template_options(),
                message=self.params.get("message"),
                error=self.params.get("error"),
            ),
        )

    def page_report_finding_new(self, cap):
        self._send_html(
            200,
            render(
                "report_finding_form.html",
                page="engagements",
                stats=self._stats(),
                mode="new",
                finding=None,
                preset_engagement_id=self.params.get("engagement_id"),
                options=api.get_report_finding_options(),
                message=self.params.get("message"),
                error=self.params.get("error"),
            ),
        )

    def page_report_finding_edit(self, cap):
        finding = api.get_report_finding_detail(cap["finding_id"])
        if not finding:
            self._send_html(404, "<h1>Finding not found</h1>")
            return
        self._send_html(
            200,
            render(
                "report_finding_form.html",
                page="engagements",
                stats=self._stats(),
                mode="edit",
                finding=finding,
                options=api.get_report_finding_options(),
                message=self.params.get("message"),
                error=self.params.get("error"),
            ),
        )

    def page_agents(self, cap):
        self._send_html(
            200,
            render(
                "agents.html",
                page="agents",
                stats=self._stats(),
                agents=agents_mod.get_agent_history(engagement_id=self.scope),
            ),
        )

    # ----------------------------------------------------------------- #
    # POST handlers                                                      #
    # ----------------------------------------------------------------- #

    def post_create_engagement(self, cap):
        result = handle_create_reporting_engagement(
            {
                "name": self.form.get("name", ""),
                "client_name": self._blank_to_none(self.form.get("client_name")),
                "summary": self._blank_to_none(self.form.get("summary")),
            }
        )
        referer = self.headers.get("Referer", "/reporting/findings")
        if "error" in result:
            self._redirect_with_message(referer, error=result["error"])
        else:
            self._redirect_with_message(referer, message="Engagement created")

    def post_create_finding(self, cap):
        payload = self._finding_payload_from_form(self.form)
        payload["created_by"] = "dashboard"
        result = handle_create_reporting_finding(payload)
        if "error" in result:
            self._redirect_with_message("/reporting/findings/new", error=result["error"])
        else:
            finding_id = result["finding"]["finding_id"]
            self._redirect_with_message(
                f"/reporting/findings/{finding_id}/edit", message="Finding created"
            )

    def post_request_docx(self, cap):
        finding_id = self._blank_to_none(self.form.get("finding_id"))
        args = {
            "engagement_id": self._blank_to_none(self.form.get("engagement_id")),
            "status": self._blank_to_none(self.form.get("status")),
            "target": self._blank_to_none(self.form.get("target")),
        }
        if finding_id:
            args["finding_ids"] = [finding_id]
            args.pop("engagement_id", None)
            args.pop("status", None)
        result = handle_request_reporting_docx(args)
        if "error" in result:
            self._redirect_with_message(
                self.headers.get("Referer", "/reporting/findings"), error=result["error"]
            )
        else:
            self._redirect(f"/executions#exec:{result['execution_id']}")

    def post_add_asset(self, cap):
        engagement_id = cap["engagement_id"]
        workspace_url = f"/reporting/engagements/{engagement_id}"
        value = self._blank_to_none(self.form.get("value"))
        if not value:
            self._redirect_with_message(workspace_url, error="Asset value is required")
            return
        try:
            create_asset(
                value,
                engagement_id=engagement_id,
                kind=self.form.get("kind", "host"),
                description=self._blank_to_none(self.form.get("description")),
            )
            self._redirect_with_message(workspace_url, message="Scope asset added")
        except (sqlite3.IntegrityError, ValueError) as exc:
            self._redirect_with_message(workspace_url, error=str(exc))

    def post_delete_asset(self, cap):
        workspace_url = f"/reporting/engagements/{cap['engagement_id']}"
        delete_asset(cap["asset_id"])
        self._redirect_with_message(workspace_url, message="Scope asset removed")

    def post_finding_status(self, cap):
        finding_id = cap["finding_id"]
        result = handle_update_reporting_finding(
            {
                "finding_id": finding_id,
                "status": self.form.get("new_status", ""),
                "updated_by": "dashboard",
            }
        )
        engagement_id = result["finding"].get("engagement_id") if "finding" in result else None
        findings = api.get_engagement_findings(
            engagement_id,
            status=self._blank_to_none(self.form.get("status")),
            severity=self._blank_to_none(self.form.get("severity")),
            query=self._blank_to_none(self.form.get("q")),
        )
        self._send_html(
            200,
            render(
                "partials/engagement_findings_list.html",
                findings=findings,
                options=api.get_report_finding_options(),
                engagement_id=engagement_id,
            ),
        )

    def post_update_finding(self, cap):
        finding_id = cap["finding_id"]
        payload = self._finding_payload_from_form(self.form)
        payload["finding_id"] = finding_id
        payload["updated_by"] = "dashboard"
        result = handle_update_reporting_finding(payload)
        edit_url = f"/reporting/findings/{finding_id}/edit"
        if "error" in result:
            self._redirect_with_message(edit_url, error=result["error"])
        else:
            self._redirect_with_message(edit_url, message="Finding updated")

    def post_finding_evidence(self, cap):
        finding_id = cap["finding_id"]
        result = handle_add_reporting_finding_evidence(
            {
                "finding_id": finding_id,
                "kind": self.form.get("kind", "note"),
                "title": self._blank_to_none(self.form.get("title")),
                "body": self._blank_to_none(self.form.get("body")),
                "artifact_path": self._blank_to_none(self.form.get("artifact_path")),
                "url": self._blank_to_none(self.form.get("url")),
                "source_execution_id": self._blank_to_none(self.form.get("source_execution_id")),
                "created_by": "dashboard",
            }
        )
        edit_url = f"/reporting/findings/{finding_id}/edit"
        if "error" in result:
            self._redirect_with_message(edit_url, error=result["error"])
        else:
            self._redirect_with_message(edit_url, message="Evidence added")

    def post_finding_reference(self, cap):
        finding_id = cap["finding_id"]
        result = handle_add_reporting_finding_reference(
            {
                "finding_id": finding_id,
                "label": self._blank_to_none(self.form.get("label")),
                "url": self.form.get("url", ""),
            }
        )
        edit_url = f"/reporting/findings/{finding_id}/edit"
        if "error" in result:
            self._redirect_with_message(edit_url, error=result["error"])
        else:
            self._redirect_with_message(edit_url, message="Reference added")

    def post_create_template(self, cap):
        payload = self._template_payload_from_form(self.form)
        payload["created_by"] = "dashboard"
        try:
            template = create_finding_template(**payload)
        except ValueError as exc:
            self._redirect_with_message("/reporting/templates/new", error=str(exc))
            return
        self._redirect_with_message(
            f"/reporting/templates/{template['template_id']}/edit", message="Template created"
        )

    def post_update_template(self, cap):
        template_id = cap["template_id"]
        edit_url = f"/reporting/templates/{template_id}/edit"
        payload = self._template_payload_from_form(self.form)
        try:
            result = update_finding_template(template_id, updated_by="dashboard", **payload)
        except ValueError as exc:
            self._redirect_with_message(edit_url, error=str(exc))
            return
        if result is None:
            self._send_html(404, "<h1>Template not found</h1>")
            return
        self._redirect_with_message(edit_url, message="Template updated")

    def post_delete_template(self, cap):
        delete_finding_template(cap["template_id"])
        self._redirect_with_message("/reporting/templates", message="Template deleted")

    def post_use_template(self, cap):
        template = get_finding_template(cap["template_id"])
        if not template:
            self._send_html(404, "<h1>Template not found</h1>")
            return
        engagement_id = self._blank_to_none(self.form.get("engagement_id"))
        # Ignore an unknown engagement rather than creating a dangling reference.
        if engagement_id and not api.get_engagement(engagement_id):
            engagement_id = None
        payload = template_to_finding_payload(template)
        finding = create_finding(engagement_id=engagement_id, created_by="dashboard", **payload)
        self._redirect_with_message(
            f"/reporting/findings/{finding['finding_id']}/edit",
            message="Finding created from template — set the affected target and add evidence",
        )

    def post_finding_save_as_template(self, cap):
        finding = get_finding(cap["finding_id"])
        edit_url = f"/reporting/findings/{cap['finding_id']}/edit"
        if not finding:
            self._send_html(404, "<h1>Finding not found</h1>")
            return
        payload = finding_to_template_payload(finding)
        payload["source"] = "finding"
        payload["created_by"] = "dashboard"
        try:
            create_finding_template(**payload)
        except ValueError as exc:
            self._redirect_with_message(edit_url, error=str(exc))
            return
        self._redirect_with_message(edit_url, message="Saved to the template library")

    def post_execution_engagement(self, cap):
        execution_id = cap["execution_id"]
        engagement_id = self._blank_to_none(self.form.get("engagement_id"))
        # Ignore an unknown engagement rather than tagging with a dangling id.
        if engagement_id and not api.get_engagement(engagement_id):
            engagement_id = None
        update_execution(execution_id, {"engagement_id": engagement_id})
        detail = api.get_execution_detail(execution_id)
        if detail is None:
            self._send_html(404, "<h1>Execution not found</h1>")
            return
        self._send_html(200, render("partials/execution_detail.html", e=detail))

    # ----------------------------------------------------------------- #
    # Helpers                                                            #
    # ----------------------------------------------------------------- #

    def _stats(self):
        return api.get_stats(engagement_id=self.scope)

    def _scope_id(self):
        """Current engagement scope from the tm_scope cookie, validated.

        Returns the engagement_id when the cookie names a real engagement, else
        None (an unknown/stale id would otherwise scope every metric to zero).
        """
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            key, _, value = part.strip().partition("=")
            if key == "tm_scope" and value:
                engagement_id = unquote(value)
                if engagement_id and api.get_engagement(engagement_id):
                    return engagement_id
                return None
        return None

    def _parse_form(self, body):
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return {k: (v if len(v) > 1 else v[0]) for k, v in parsed.items()}

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
            "category": self._blank_to_none(form.get("category")),
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

    def _template_payload_from_form(self, form):
        return {
            "title": form.get("title", ""),
            "severity": form.get("severity", "Info"),
            "category": self._blank_to_none(form.get("category")),
            "description": form.get("description", ""),
            "impact": form.get("impact", ""),
            "proof_of_concept": form.get("proof_of_concept", ""),
            "remediation": form.get("remediation", ""),
            "cvss_score": self._blank_to_none(form.get("cvss_score")),
            "cvss_vector": self._blank_to_none(form.get("cvss_vector")),
            "references": self._references_from_form(form),
        }

    @staticmethod
    def _references_from_form(form):
        """Parse the references textarea (one 'label|url' or 'url' per line)."""
        raw = form.get("references", "")
        if isinstance(raw, list):
            raw = raw[0] if raw else ""
        refs = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                label, _, url = line.partition("|")
                refs.append({"label": label.strip() or None, "url": url.strip()})
            else:
                refs.append({"label": None, "url": line})
        return refs

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

    def _send_download(self, filepath):
        content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        with open(filepath, "rb") as f:
            data = f.read()
        filename = os.path.basename(filepath)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
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

    def _send_json(self, status, data):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        logging.info(format % args)

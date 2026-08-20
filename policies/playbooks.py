"""Built-in playbooks: named, ordered skill sequences.

A playbook expands into a linear chain of executions for one target — step N
depends on step N-1, so a worker runs them in order as each unblocks (see
``tools/request_playbook.py`` and the ``depends_on`` machinery in
``state/state.py``). This turns a multi-call methodology ("tech-detect, then
fuzz, then...") into a single ``request_playbook`` call.

Each step is a partial ``request_security_action`` payload: the tool fills in
``target``, ``engagement_id``, and ``depends_on`` at expansion time. Steps must
be phase-monotonic (reconnaissance → enumeration → exploitation → …) because the
per-target phase policy is enforced as the chain is created. Skills here rely on
each skill defaulting its primary argument to the execution target, so empty
``arguments`` is intentional and runnable.
"""

PLAYBOOKS = {
    "web-recon": {
        "description": (
            "Web target baseline: HTTP tech-detect (recon) then content discovery "
            "fuzzing (enumeration)."
        ),
        "steps": [
            {
                "phase": "reconnaissance",
                "agent_role": "recon",
                "action_type": "skill",
                "skill": "web.HttpxDetect",
                "arguments": {},
                "allow_complex_tooling": True,
                "justification": (
                    "Baseline HTTP fingerprint of the in-scope web target: capture server "
                    "headers, detected technologies, page title, and final URL to guide "
                    "subsequent enumeration."
                ),
                "expected_output": (
                    "HTTP status, detected technologies, response headers, and final "
                    "redirected URL for the target."
                ),
            },
            {
                "phase": "enumeration",
                "agent_role": "enumeration",
                "action_type": "skill",
                "skill": "web.FfufFuzz",
                "arguments": {},
                "justification": (
                    "Content discovery against the web target using a common-paths wordlist "
                    "to surface non-linked endpoints, admin panels, and backup files for "
                    "follow-up review."
                ),
                "expected_output": (
                    "Discovered paths with their HTTP status codes and response sizes."
                ),
            },
        ],
    },
    "aws-privesc-recon": {
        "description": (
            "AWS identity attack-surface map from a set of credentials: account "
            "audit + loot sweep (recon) then IAM privilege-escalation path finding "
            "(enumeration). Read-only — it maps the privesc paths; it does not walk "
            "them. Pass the profile/region via each step's arguments, or rely on the "
            "worker's ambient credentials. Target is a nominal label (account id/ARN)."
        ),
        "steps": [
            {
                "phase": "reconnaissance",
                "agent_role": "recon",
                "action_type": "skill",
                "skill": "cloud.AwsCliAudit",
                "arguments": {},
                "justification": (
                    "Baseline the compromised AWS identity: resolve the caller with STS, "
                    "then inventory S3 (recursing buckets to flag keys, .env, tfstate and "
                    "other loot), IAM users, Secrets Manager, and DynamoDB tables to scope "
                    "what this principal can already reach."
                ),
                "expected_output": (
                    "Caller identity/ARN, bucket list with flagged interesting object keys, "
                    "IAM user names, Secrets Manager secret names, and DynamoDB table names."
                ),
            },
            {
                "phase": "enumeration",
                "agent_role": "enumeration",
                "action_type": "skill",
                "skill": "cloud.IamPrivescFinder",
                "arguments": {},
                "justification": (
                    "Walk the caller's attached and inline IAM policies (every policy "
                    "version, not just the default) and flag known privilege-escalation "
                    "primitives — SetDefaultPolicyVersion, PassRole+CreateFunction, "
                    "AttachUserPolicy and the rest — to identify a path to higher privilege."
                ),
                "expected_output": (
                    "List of flagged privesc primitives, each with the enabling action, the "
                    "technique it unlocks, and the source policy/version it came from."
                ),
            },
        ],
    },
    "mobile-static-assessment": {
        "description": (
            "Full Android APK static pass for one app: manifest triage (recon) then "
            "decompile, secret sweep, and two nuclei passes (enumeration) — a fast "
            "first-party pass for app-code signal plus a longer full-tree pass for "
            "library/resource coverage. Drop exactly one .apk in the agent's session "
            "mount (spawn with session_dir); every step auto-discovers it. Target is a "
            "nominal label (the app package, e.g. com.example.app)."
        ),
        "steps": [
            {
                "phase": "reconnaissance",
                "agent_role": "recon",
                "action_type": "mobile_skill",
                "skill": "mobile.ManifestScan",
                "arguments": {},
                "justification": (
                    "Parse AndroidManifest.xml to baseline the app: package, min/target "
                    "SDK, debuggable/allowBackup/cleartext flags, exported components with "
                    "their permission guards, custom permissions, and declared deeplinks."
                ),
                "expected_output": (
                    "Package, SDK versions, application security flags, exported "
                    "components, custom permissions, deeplinks, and risk notes."
                ),
            },
            {
                "phase": "enumeration",
                "agent_role": "enumeration",
                "action_type": "mobile_skill",
                "skill": "mobile.ApkDecompile",
                "arguments": {"output_dir": "/loot/mobile-assessment"},
                "justification": (
                    "Decode the APK (manifest, resources, and smali) into a shared "
                    "directory so the secret sweep and nuclei passes reuse one decompiled "
                    "tree instead of each decoding the APK again."
                ),
                "expected_output": (
                    "A decompiled tree at /loot/mobile-assessment and its file count."
                ),
            },
            {
                "phase": "enumeration",
                "agent_role": "enumeration",
                "action_type": "mobile_skill",
                "skill": "mobile.SecretScan",
                "arguments": {"source_dir": "/loot/mobile-assessment"},
                "justification": (
                    "Regex-sweep the whole decompiled tree (including res/values) for "
                    "hardcoded secrets — API/cloud keys, private keys, JWTs, Firebase "
                    "URLs — and collect referenced HTTP endpoints for review."
                ),
                "expected_output": (
                    "Redacted secret matches with file/line, and the distinct endpoints "
                    "found across the app."
                ),
            },
            {
                "phase": "enumeration",
                "agent_role": "enumeration",
                "action_type": "mobile_skill",
                "skill": "mobile.MobileNucleiScan",
                "arguments": {"source_dir": "/loot/mobile-assessment", "first_party": True},
                "justification": (
                    "Run the mobile nuclei template set scoped to the app's own package "
                    "code (first-party), which finishes fast and surfaces the highest-value "
                    "app-code signatures (WebView/JS misuse, insecure config) without "
                    "library noise."
                ),
                "expected_output": (
                    "Nuclei matches within the app's own code, with template id, severity, "
                    "and matched location."
                ),
            },
            {
                "phase": "enumeration",
                "agent_role": "enumeration",
                "action_type": "mobile_skill",
                "skill": "mobile.MobileNucleiScan",
                "arguments": {"source_dir": "/loot/mobile-assessment", "timeout": 600},
                "justification": (
                    "Run the mobile nuclei template set across the full decompiled tree "
                    "(bundled SDKs and resources included) with an extended budget so "
                    "library/third-party findings the first-party pass skips are still "
                    "covered; returns bounded partial results if it hits the wall clock."
                ),
                "expected_output": (
                    "Nuclei matches across the whole app (including third-party code), "
                    "with a timed_out flag indicating whether coverage was complete."
                ),
            },
        ],
    },
    "subdomain-recon": {
        "description": (
            "Domain attack-surface mapping: passive subdomain enumeration (recon) then "
            "active DNS brute-force (enumeration)."
        ),
        "steps": [
            {
                "phase": "reconnaissance",
                "agent_role": "recon",
                "action_type": "skill",
                "skill": "subdomain.SubfinderEnum",
                "arguments": {},
                "justification": (
                    "Passive subdomain enumeration for the target domain via public sources "
                    "to map externally-visible attack surface before any active probing."
                ),
                "expected_output": "List of discovered subdomains for the domain.",
            },
            {
                "phase": "enumeration",
                "agent_role": "enumeration",
                "action_type": "skill",
                "skill": "subdomain.GobusterDns",
                "arguments": {},
                "justification": (
                    "Active DNS brute-force of the target domain to discover subdomains not "
                    "present in passive sources, expanding the enumerated attack surface."
                ),
                "expected_output": ("Resolvable subdomains discovered via DNS brute force."),
            },
        ],
    },
}


def get_playbook(name):
    """Return the playbook dict for ``name``, or None."""
    return PLAYBOOKS.get(name)


def list_playbooks():
    """Return [{name, description, steps}] for every built-in playbook."""
    return [
        {"name": name, "description": pb["description"], "steps": len(pb["steps"])}
        for name, pb in PLAYBOOKS.items()
    ]

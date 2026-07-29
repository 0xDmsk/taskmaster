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
                "expected_output": (
                    "Resolvable subdomains discovered via DNS brute force."
                ),
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

LIFECYCLE_TRANSITIONS = {
    "QUEUED": {"CLAIMED", "CANCELLED"},
    "CLAIMED": {"RUNNING", "CANCELLED"},
    "RUNNING": {"COMPLETED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}

SECURITY_PHASE_TRANSITIONS = {
    None: {"reconnaissance"},
    "reconnaissance": {"reconnaissance", "enumeration"},
    "enumeration": {"enumeration", "exploitation"},
    "exploitation": {"exploitation", "post_exploitation"},
    "post_exploitation": {"post_exploitation", "reporting"},
    "reporting": {"reporting"},
}


def is_lifecycle_allowed(current_status, requested_status):
    allowed = LIFECYCLE_TRANSITIONS.get(current_status, set())
    return requested_status in allowed


def is_security_phase_allowed(current_phase, requested_phase):
    # Allow transitioning from None (first action)
    allowed = SECURITY_PHASE_TRANSITIONS.get(current_phase, set())
    return requested_phase in allowed
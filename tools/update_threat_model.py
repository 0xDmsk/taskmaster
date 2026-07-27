import sqlite3

from state.reporting import update_threat_model

_FIELDS = {
    "engagement_id",
    "title",
    "methodology",
    "status",
    "review_date",
    "scope",
    "out_of_scope",
    "summary",
}


def handle_update_threat_model(args):
    threat_model_id = args.get("threat_model_id")
    if not threat_model_id:
        return {"error": "threat_model_id is required"}
    updates = {field: args[field] for field in _FIELDS if field in args}
    try:
        model = update_threat_model(
            threat_model_id,
            updated_by=args.get("updated_by", "system"),
            **updates,
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}
    if not model:
        return {"error": "Threat model not found"}
    return {"status": "updated", "threat_model": model}

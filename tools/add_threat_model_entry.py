import sqlite3

from state.reporting import add_threat_model_entry


def handle_add_threat_model_entry(args):
    threat_model_id = args.get("threat_model_id")
    entity_type = args.get("entity_type")
    if not threat_model_id or not entity_type:
        return {"error": "threat_model_id and entity_type are required"}
    fields = dict(args.get("fields") or {})
    try:
        entry = add_threat_model_entry(
            threat_model_id,
            entity_type,
            ref=args.get("ref"),
            created_by=args.get("created_by", "system"),
            **fields,
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}
    return {"status": "created", "entity_type": entity_type, "entry": entry}

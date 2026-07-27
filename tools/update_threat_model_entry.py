import sqlite3

from state.reporting import update_threat_model_entry


def handle_update_threat_model_entry(args):
    threat_model_id = args.get("threat_model_id")
    entity_type = args.get("entity_type")
    ref = args.get("ref")
    if not threat_model_id or not entity_type or not ref:
        return {"error": "threat_model_id, entity_type, and ref are required"}
    fields = dict(args.get("fields") or {})
    try:
        entry = update_threat_model_entry(
            threat_model_id,
            entity_type,
            ref,
            updated_by=args.get("updated_by", "system"),
            **fields,
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}
    if entry is None:
        return {"error": f"No {entity_type} '{ref}' in threat model {threat_model_id}"}
    return {"status": "updated", "entity_type": entity_type, "entry": entry}

from state.reporting import delete_threat_model_entry


def handle_delete_threat_model_entry(args):
    threat_model_id = args.get("threat_model_id")
    entity_type = args.get("entity_type")
    ref = args.get("ref")
    if not threat_model_id or not entity_type or not ref:
        return {"error": "threat_model_id, entity_type, and ref are required"}
    try:
        removed = delete_threat_model_entry(threat_model_id, entity_type, ref)
    except ValueError as exc:
        return {"error": str(exc)}
    if not removed:
        return {"error": f"No {entity_type} '{ref}' in threat model {threat_model_id}"}
    return {"status": "deleted", "entity_type": entity_type, "ref": ref}

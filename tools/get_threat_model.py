from state.reporting import get_threat_model


def handle_get_threat_model(args):
    threat_model_id = args.get("threat_model_id")
    if not threat_model_id:
        return {"error": "threat_model_id is required"}
    model = get_threat_model(threat_model_id)
    if not model:
        return {"error": "Threat model not found"}
    return {"threat_model": model}

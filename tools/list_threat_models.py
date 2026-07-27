from state.reporting import list_threat_models


def handle_list_threat_models(args):
    models = list_threat_models(
        engagement_id=args.get("engagement_id"),
        status=args.get("status"),
    )
    return {"threat_models": models, "count": len(models)}

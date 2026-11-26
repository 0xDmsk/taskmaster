from state.surface import upsert_surface_items


def handle_upsert_surface_items(args):
    engagement_id = args.get("engagement_id")
    items = args.get("items")
    if not engagement_id:
        return {"error": "engagement_id is required"}
    if not isinstance(items, list) or not items:
        return {"error": "items must be a non-empty list"}

    try:
        stored = upsert_surface_items(
            engagement_id,
            items,
            source=args.get("source", "import"),
            default_host=args.get("default_host", ""),
            created_by=args.get("created_by", "system"),
        )
    except ValueError as exc:
        return {"error": str(exc)}

    return {
        "status": "ok",
        "count": len(stored),
        "items": [
            {"ref": i["ref"], "kind": i["kind"], "key": i["key"], "item_id": i["item_id"]}
            for i in stored
        ],
    }

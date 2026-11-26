from state.reporting import get_engagement
from state.surface import list_surface


def _compact(item, refs_by_id):
    links = item["links"]
    return {
        "ref": item["ref"],
        "kind": item["kind"],
        "name": item["name"],
        "key": item["key"],
        "parent": refs_by_id.get(item["parent_id"]),
        "attack_surface_ref": item["attack_surface_ref"] or None,
        "status": item["status"],
        "phase_counts": item["phase_counts"],
        "discovered_by": sorted(
            {l["execution_id"] for l in links if l["rel"] == "discovered" and l["execution_id"]}
        ),
        "tested_by": sorted(
            {l["execution_id"] for l in links if l["rel"] == "tested" and l["execution_id"]}
        ),
        "findings": sorted(
            {l["finding_id"] for l in links if l["rel"] == "affects" and l["finding_id"]}
        ),
    }


def handle_list_surface_items(args):
    engagement_id = args.get("engagement_id")
    if not engagement_id:
        return {"error": "engagement_id is required"}
    if not get_engagement(engagement_id):
        return {"error": f"Unknown engagement_id: {engagement_id}"}

    items = list_surface(engagement_id)
    refs_by_id = {i["item_id"]: i["ref"] for i in items}
    status, kind = args.get("status"), args.get("kind")
    rows = [
        _compact(i, refs_by_id)
        for i in items
        if (not status or i["status"] == status) and (not kind or i["kind"] == kind)
    ]
    counts = {}
    for item in items:
        if item["kind"] == "endpoint":
            counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {"engagement_id": engagement_id, "endpoint_status_counts": counts, "items": rows}

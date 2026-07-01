import sqlite3

from state.reporting import create_engagement


def handle_create_reporting_engagement(args):
    name = args.get("name")
    if not name:
        return {"error": "name is required"}

    try:
        engagement = create_engagement(
            name=name,
            engagement_id=args.get("engagement_id"),
            slug=args.get("slug"),
            client_name=args.get("client_name"),
            status=args.get("status", "active"),
            summary=args.get("summary"),
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}

    return {"status": "created", "engagement": engagement}

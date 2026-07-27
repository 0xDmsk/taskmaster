import sqlite3

from state.reporting import create_threat_model


def handle_create_threat_model(args):
    title = args.get("title")
    if not title:
        return {"error": "title is required"}
    try:
        model = create_threat_model(
            engagement_id=args.get("engagement_id"),
            title=title,
            threat_model_id=args.get("threat_model_id"),
            methodology=args.get("methodology", "STRIDE"),
            status=args.get("status", "draft"),
            review_date=args.get("review_date"),
            scope=args.get("scope", ""),
            out_of_scope=args.get("out_of_scope", ""),
            summary=args.get("summary", ""),
            created_by=args.get("created_by", "system"),
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}
    return {"status": "created", "threat_model": model}

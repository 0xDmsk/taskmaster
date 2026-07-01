from state.reporting import list_engagements


def handle_list_reporting_engagements(args):
    engagements = list_engagements(status=args.get("status"))
    return {"engagements": engagements, "count": len(engagements)}

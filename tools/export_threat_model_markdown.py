import re

from state.reporting import get_threat_model, render_threat_model_markdown


def _slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "threat-model"


def handle_export_threat_model_markdown(args):
    threat_model_id = args.get("threat_model_id")
    if not threat_model_id:
        return {"error": "threat_model_id is required"}
    model = get_threat_model(threat_model_id)
    if not model:
        return {"error": "Threat model not found"}
    markdown = render_threat_model_markdown(threat_model_id)
    return {
        "threat_model_id": threat_model_id,
        "markdown": markdown,
        "filename_suggestion": f"{_slugify(model.get('title'))}-threat-model.md",
    }

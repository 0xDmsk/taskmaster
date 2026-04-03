"""Dashboard package — Jinja2 environment setup and render helpers."""

import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
)


def render(template_name, **context):
    """Render a template to string."""
    return _env.get_template(template_name).render(**context)

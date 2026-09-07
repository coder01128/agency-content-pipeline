from __future__ import annotations

from src.config import load_config
from src.state import PipelineState
from src.tools.wordpress import get_pages


def analyze_site(state: PipelineState) -> dict:
    errors: list[str] = list(state.get("errors", []))

    try:
        settings = load_config()
    except ValueError as exc:
        errors.append(f"Config error: {exc}")
        return {"wp_existing_pages": [], "errors": errors}

    try:
        pages = get_pages(
            settings.wp_site_url,
            settings.wp_username,
            settings.wp_app_password,
        )
    except Exception as exc:
        errors.append(f"WordPress unreachable: {exc}")
        return {"wp_existing_pages": [], "errors": errors}

    return {"wp_existing_pages": pages, "errors": errors}

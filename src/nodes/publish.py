from __future__ import annotations

from src.config import load_config
from src.state import PipelineState
from src.tools.wordpress import create_draft_page, update_draft_page


def publish(state: PipelineState) -> dict:
    errors: list[str] = list(state.get("errors", []))

    try:
        settings = load_config()
    except ValueError as exc:
        errors.append(f"Config error: {exc}")
        return {"draft_urls": [], "errors": errors}

    sections = state.get("sections", [])
    existing_pages = state.get("wp_existing_pages", [])
    slug_to_id: dict[str, int] = {p["slug"]: p["id"] for p in existing_pages}

    draft_urls: list[str] = []

    for section in sections:
        try:
            target = section.get("target_page")
            if target and target in slug_to_id:
                result = update_draft_page(
                    settings.wp_site_url,
                    settings.wp_username,
                    settings.wp_app_password,
                    slug_to_id[target],
                    section["title"],
                    section["body"],
                )
            else:
                slug = target or section["title"].lower().replace(" ", "-")
                result = create_draft_page(
                    settings.wp_site_url,
                    settings.wp_username,
                    settings.wp_app_password,
                    section["title"],
                    section["body"],
                    slug,
                )
            draft_urls.append(result["link"])
        except Exception as exc:
            errors.append(f"Failed to publish '{section['title']}': {exc}")

    return {"draft_urls": draft_urls, "errors": errors}

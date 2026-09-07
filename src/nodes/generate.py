from __future__ import annotations

from src.config import load_config
from src.state import PipelineState
from src.tools.claude_tools import generate_sections


def generate(state: PipelineState) -> dict:
    errors: list[str] = list(state.get("errors", []))
    attempts = state.get("generation_attempts", 0) + 1

    try:
        settings = load_config()
    except ValueError as exc:
        errors.append(f"Config error: {exc}")
        return {"sections": [], "generation_attempts": attempts, "errors": errors}

    brief = state.get("brief_content", "")
    existing_pages = state.get("wp_existing_pages", [])
    feedback = state.get("generation_feedback")

    try:
        sections = generate_sections(
            brief=brief,
            existing_pages=existing_pages,
            feedback=feedback if feedback else None,
            api_key=settings.anthropic_api_key,
        )
    except Exception as exc:
        errors.append(f"Generation failed: {exc}")
        return {"sections": [], "generation_attempts": attempts, "errors": errors}

    return {"sections": sections, "generation_attempts": attempts, "errors": errors}

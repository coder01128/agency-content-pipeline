from __future__ import annotations

import re
from pathlib import Path

from src.state import PipelineState


def _extract_client_name(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            heading = line.lstrip("# ").strip()
            heading = re.sub(r"^Client Brief:\s*", "", heading, flags=re.IGNORECASE)
            if heading:
                return heading
    first_line = text.strip().split("\n", 1)[0].strip()
    return first_line if first_line else "Unknown Client"


def intake(state: PipelineState) -> dict:
    source = state.get("brief_source", "")
    errors: list[str] = list(state.get("errors", []))

    # TODO: Google Docs integration — if source starts with
    # "https://docs.google.com", call google_docs.read_doc() here.

    path = Path(source)
    if path.suffix in (".md", ".txt"):
        if not path.is_file():
            errors.append(f"Brief file not found: {source}")
            return {"brief_content": "", "client_name": "Unknown Client", "errors": errors}
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"Failed to read brief file: {exc}")
            return {"brief_content": "", "client_name": "Unknown Client", "errors": errors}
    else:
        content = source

    if not content.strip():
        errors.append("Brief source is empty.")
        return {"brief_content": "", "client_name": "Unknown Client", "errors": errors}

    client_name = _extract_client_name(content)
    return {"brief_content": content, "client_name": client_name, "errors": errors}

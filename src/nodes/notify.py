from __future__ import annotations

import httpx

from src.config import load_config
from src.state import PipelineState


def notify(state: PipelineState) -> dict:
    errors: list[str] = list(state.get("errors", []))
    client = state.get("client_name", "Unknown")
    urls = state.get("draft_urls", [])

    summary_lines = [
        f"=== Pipeline Complete: {client} ===",
        f"Drafts created: {len(urls)}",
    ]
    for url in urls:
        summary_lines.append(f"  - {url}")

    if errors:
        summary_lines.append(f"Errors: {len(errors)}")

    summary = "\n".join(summary_lines)
    print(f"\n{summary}\n")

    try:
        settings = load_config()
    except ValueError:
        return {"notification_sent": True, "errors": errors}

    if settings.slack_webhook_url:
        try:
            httpx.post(
                settings.slack_webhook_url,
                json={"text": summary},
                timeout=10.0,
            )
        except Exception as exc:
            errors.append(f"Slack notification failed: {exc}")

    return {"notification_sent": True, "errors": errors}

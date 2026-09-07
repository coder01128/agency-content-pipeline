from __future__ import annotations

from src.state import PipelineState


def publish(state: PipelineState) -> dict:
    return {"draft_urls": []}

from __future__ import annotations

from src.state import PipelineState


def notify(state: PipelineState) -> dict:
    return {"notification_sent": True}

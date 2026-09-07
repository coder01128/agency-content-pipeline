from __future__ import annotations

from src.state import PipelineState


def review(state: PipelineState) -> dict:
    return {"approval_status": "approved"}

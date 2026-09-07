from __future__ import annotations

from src.state import PipelineState


def intake(state: PipelineState) -> dict:
    return {"brief_content": "stub brief content", "client_name": "Stub Client"}

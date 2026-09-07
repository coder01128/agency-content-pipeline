from __future__ import annotations

from src.state import PipelineState


def generate(state: PipelineState) -> dict:
    attempts = state.get("generation_attempts", 0) + 1
    return {"sections": [], "generation_attempts": attempts}

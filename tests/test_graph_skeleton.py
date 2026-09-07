"""Test T-02: Graph skeleton with conditional routing."""
from __future__ import annotations

import src.graph as graph_mod
from src.graph import compile_graph
from src.state import PipelineState


def test_happy_path_all_nodes_fire():
    app = compile_graph()
    initial: PipelineState = {
        "brief_source": "test brief",
        "wp_site_url": "https://example.com",
        "generation_attempts": 0,
        "errors": [],
    }
    result = app.invoke(initial)

    assert result["brief_content"] == "stub brief content"
    assert result["client_name"] == "Stub Client"
    assert result["wp_existing_pages"] == []
    assert result["generation_attempts"] == 1
    assert result["approval_status"] == "approved"
    assert result["draft_urls"] == []
    assert result["notification_sent"] is True


def test_reject_loops_back_to_generate(monkeypatch):
    call_count = {"review": 0}

    def review_reject_then_approve(state: PipelineState) -> dict:
        call_count["review"] += 1
        if call_count["review"] == 1:
            return {
                "approval_status": "rejected",
                "generation_feedback": "make it shorter",
            }
        return {"approval_status": "approved"}

    monkeypatch.setattr(graph_mod, "review", review_reject_then_approve)

    app = graph_mod.build_graph().compile()

    initial: PipelineState = {
        "brief_source": "test brief",
        "wp_site_url": "https://example.com",
        "generation_attempts": 0,
        "errors": [],
    }
    result = app.invoke(initial)

    assert result["generation_attempts"] == 2
    assert result["approval_status"] == "approved"
    assert result["notification_sent"] is True


def test_max_attempts_exits_without_publishing(monkeypatch):
    def always_reject(state: PipelineState) -> dict:
        return {"approval_status": "rejected", "generation_feedback": "no"}

    monkeypatch.setattr(graph_mod, "review", always_reject)

    app = graph_mod.build_graph().compile()

    initial: PipelineState = {
        "brief_source": "test brief",
        "wp_site_url": "https://example.com",
        "generation_attempts": 0,
        "errors": [],
    }
    result = app.invoke(initial)

    assert result["generation_attempts"] == 3
    assert result["approval_status"] == "rejected"
    assert result.get("notification_sent") is not True

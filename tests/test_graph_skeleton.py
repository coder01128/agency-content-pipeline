"""Test T-02: Graph skeleton — conditional routing still works with wired nodes."""
from __future__ import annotations

from unittest.mock import patch

import src.graph as graph_mod
from src.graph import compile_graph
from src.state import PipelineState


@patch("builtins.input", return_value="a")
@patch("src.nodes.generate.generate_sections", return_value=[])
@patch("src.nodes.generate.load_config")
@patch("src.nodes.analyze_site.load_config")
@patch("src.nodes.analyze_site.get_pages", return_value=[])
def test_happy_path_all_nodes_fire(
    mock_wp_pages, mock_az_config, mock_gen_config, mock_gen_sections, mock_input
):
    from src.config import Settings

    cfg = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://example.com",
        wp_username="admin",
        wp_app_password="pass",
    )
    mock_az_config.return_value = cfg
    mock_gen_config.return_value = cfg

    app = compile_graph()
    initial: PipelineState = {
        "brief_source": "# Test Client\n\nBuild a site.",
        "wp_site_url": "https://example.com",
        "generation_attempts": 0,
        "errors": [],
    }
    result = app.invoke(initial)

    assert result["brief_content"] == "# Test Client\n\nBuild a site."
    assert result["client_name"] == "Test Client"
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

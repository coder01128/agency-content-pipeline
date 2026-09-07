"""T-12 + T-13: End-to-end integration tests and error handling hardening."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.graph import compile_graph
from src.state import PipelineState, Section

SAMPLE_BRIEF = str(Path(__file__).parent.parent / "examples" / "sample_brief.md")

MOCK_SECTIONS: list[Section] = [
    {
        "title": "Home",
        "body": "<h1>Welcome to GreenScape</h1><p>Phoenix landscaping.</p>",
        "meta_description": "GreenScape Landscaping in Phoenix AZ.",
        "target_page": "home",
    },
    {
        "title": "Services",
        "body": "<h1>Our Services</h1><p>Residential and commercial.</p>",
        "meta_description": "Landscaping services in Phoenix.",
        "target_page": None,
    },
]

MOCK_WP_PAGES = [
    {"id": 2, "slug": "home", "title": "Home", "status": "publish"},
    {"id": 5, "slug": "contact", "title": "Contact", "status": "publish"},
]


def _make_settings():
    from src.config import Settings

    return Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )


def _wp_create_response(call_num: int) -> dict:
    return {
        "id": 20 + call_num,
        "slug": f"page-{call_num}",
        "title": "Services",
        "status": "draft",
        "link": f"https://test.local/?page_id={20 + call_num}",
    }


def _wp_update_response() -> dict:
    return {
        "id": 2,
        "slug": "home",
        "title": "Home",
        "status": "draft",
        "link": "https://test.local/home/",
    }


# ---------------------------------------------------------------------------
# T-12: Integration tests
# ---------------------------------------------------------------------------


@patch("builtins.input", return_value="a")
@patch("src.nodes.notify.load_config")
@patch("src.nodes.publish.update_draft_page", return_value=_wp_update_response())
@patch("src.nodes.publish.create_draft_page", return_value=_wp_create_response(1))
@patch("src.nodes.publish.load_config")
@patch("src.nodes.generate.generate_sections", return_value=MOCK_SECTIONS)
@patch("src.nodes.generate.load_config")
@patch("src.nodes.analyze_site.get_pages", return_value=MOCK_WP_PAGES)
@patch("src.nodes.analyze_site.load_config")
def test_happy_path_e2e(
    mock_az_cfg, mock_az_pages,
    mock_gen_cfg, mock_gen_sections,
    mock_pub_cfg, mock_pub_create, mock_pub_update,
    mock_notify_cfg, mock_input,
):
    cfg = _make_settings()
    for m in (mock_az_cfg, mock_gen_cfg, mock_pub_cfg, mock_notify_cfg):
        m.return_value = cfg

    app = compile_graph()
    result = app.invoke({
        "brief_source": SAMPLE_BRIEF,
        "wp_site_url": "https://test.local",
        "generation_attempts": 0,
        "errors": [],
    })

    assert result["approval_status"] == "approved"
    assert result["notification_sent"] is True
    assert len(result["draft_urls"]) == 2
    assert result["generation_attempts"] == 1
    assert result["client_name"] == "GreenScape Landscaping"
    assert "GreenScape" in result["brief_content"]


@patch("src.nodes.notify.load_config")
@patch("src.nodes.publish.update_draft_page", return_value=_wp_update_response())
@patch("src.nodes.publish.create_draft_page", return_value=_wp_create_response(1))
@patch("src.nodes.publish.load_config")
@patch("src.nodes.generate.generate_sections", return_value=MOCK_SECTIONS)
@patch("src.nodes.generate.load_config")
@patch("src.nodes.analyze_site.get_pages", return_value=MOCK_WP_PAGES)
@patch("src.nodes.analyze_site.load_config")
def test_reject_then_approve_e2e(
    mock_az_cfg, mock_az_pages,
    mock_gen_cfg, mock_gen_sections,
    mock_pub_cfg, mock_pub_create, mock_pub_update,
    mock_notify_cfg, monkeypatch,
):
    cfg = _make_settings()
    for m in (mock_az_cfg, mock_gen_cfg, mock_pub_cfg, mock_notify_cfg):
        m.return_value = cfg

    inputs = iter(["r", "shorter copy", "a"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    app = compile_graph()
    result = app.invoke({
        "brief_source": SAMPLE_BRIEF,
        "wp_site_url": "https://test.local",
        "generation_attempts": 0,
        "errors": [],
    })

    assert result["generation_attempts"] == 2
    assert result["approval_status"] == "approved"
    assert len(result["draft_urls"]) == 2
    assert mock_gen_sections.call_count == 2


@patch("src.nodes.generate.generate_sections", return_value=MOCK_SECTIONS)
@patch("src.nodes.generate.load_config")
@patch("src.nodes.analyze_site.get_pages", return_value=MOCK_WP_PAGES)
@patch("src.nodes.analyze_site.load_config")
def test_triple_reject_exits_e2e(
    mock_az_cfg, mock_az_pages,
    mock_gen_cfg, mock_gen_sections,
    monkeypatch,
):
    cfg = _make_settings()
    mock_az_cfg.return_value = cfg
    mock_gen_cfg.return_value = cfg

    inputs = iter(["r", "fb1", "r", "fb2", "r", "fb3"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    app = compile_graph()
    result = app.invoke({
        "brief_source": SAMPLE_BRIEF,
        "wp_site_url": "https://test.local",
        "generation_attempts": 0,
        "errors": [],
    })

    assert result["generation_attempts"] == 3
    assert result["approval_status"] == "rejected"
    assert result.get("draft_urls", []) == []
    assert result.get("notification_sent") is not True
    assert mock_gen_sections.call_count == 3


# ---------------------------------------------------------------------------
# T-13: Error handling hardening
# ---------------------------------------------------------------------------


@patch("builtins.input", return_value="a")
@patch("src.nodes.notify.load_config")
@patch("src.nodes.publish.create_draft_page", return_value=_wp_create_response(1))
@patch("src.nodes.publish.load_config")
@patch("src.nodes.generate.generate_sections", return_value=MOCK_SECTIONS)
@patch("src.nodes.generate.load_config")
@patch("src.nodes.analyze_site.get_pages", side_effect=ConnectionError("Connection refused"))
@patch("src.nodes.analyze_site.load_config")
def test_graph_completes_when_wp_unreachable(
    mock_az_cfg, mock_az_pages,
    mock_gen_cfg, mock_gen_sections,
    mock_pub_cfg, mock_pub_create,
    mock_notify_cfg, mock_input,
):
    cfg = _make_settings()
    for m in (mock_az_cfg, mock_gen_cfg, mock_pub_cfg, mock_notify_cfg):
        m.return_value = cfg

    app = compile_graph()
    result = app.invoke({
        "brief_source": SAMPLE_BRIEF,
        "wp_site_url": "https://test.local",
        "generation_attempts": 0,
        "errors": [],
    })

    assert result["notification_sent"] is True
    assert any("unreachable" in e.lower() for e in result["errors"])


@patch("builtins.input", return_value="a")
@patch("src.nodes.notify.load_config")
@patch("src.nodes.publish.create_draft_page", return_value=_wp_create_response(1))
@patch("src.nodes.publish.load_config")
@patch("src.nodes.generate.generate_sections", side_effect=RuntimeError("Malformed response"))
@patch("src.nodes.generate.load_config")
@patch("src.nodes.analyze_site.get_pages", return_value=MOCK_WP_PAGES)
@patch("src.nodes.analyze_site.load_config")
def test_graph_completes_when_claude_returns_garbage(
    mock_az_cfg, mock_az_pages,
    mock_gen_cfg, mock_gen_sections,
    mock_pub_cfg, mock_pub_create,
    mock_notify_cfg, mock_input,
):
    cfg = _make_settings()
    for m in (mock_az_cfg, mock_gen_cfg, mock_pub_cfg, mock_notify_cfg):
        m.return_value = cfg

    app = compile_graph()
    result = app.invoke({
        "brief_source": SAMPLE_BRIEF,
        "wp_site_url": "https://test.local",
        "generation_attempts": 0,
        "errors": [],
    })

    assert result["notification_sent"] is True
    assert any("generation failed" in e.lower() for e in result["errors"])
    assert result["sections"] == []


def test_config_validation_prints_clear_errors():
    import os

    clean_env = {k: v for k, v in os.environ.items()}
    for var in ("ANTHROPIC_API_KEY", "WP_SITE_URL", "WP_USERNAME", "WP_APP_PASSWORD"):
        clean_env.pop(var, None)

    result = subprocess.run(
        [sys.executable, "-m", "src.config"],
        capture_output=True,
        text=True,
        env=clean_env,
        cwd=str(Path(__file__).parent.parent),
    )

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY" in combined
    assert "MISSING" in combined

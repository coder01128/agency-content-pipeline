"""Tests for T-06 (intake) and T-07 (analyze_site) wired nodes."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.nodes.intake import intake
from src.state import PipelineState

SAMPLE_BRIEF = Path(__file__).parent.parent / "examples" / "sample_brief.md"


# --- T-06: intake node ---


def test_intake_reads_local_md_file() -> None:
    state: PipelineState = {
        "brief_source": str(SAMPLE_BRIEF),
        "errors": [],
    }
    result = intake(state)

    assert "GreenScape" in result["brief_content"]
    assert result["client_name"] == "GreenScape Landscaping"
    assert result["errors"] == []


def test_intake_uses_raw_text() -> None:
    state: PipelineState = {
        "brief_source": "# Acme Corp\n\nBuild us a website.",
        "errors": [],
    }
    result = intake(state)

    assert result["brief_content"] == "# Acme Corp\n\nBuild us a website."
    assert result["client_name"] == "Acme Corp"


def test_intake_handles_missing_file() -> None:
    state: PipelineState = {
        "brief_source": "nonexistent_file.md",
        "errors": [],
    }
    result = intake(state)

    assert result["brief_content"] == ""
    assert result["client_name"] == "Unknown Client"
    assert any("not found" in e.lower() or "failed" in e.lower() for e in result["errors"])


def test_intake_strips_client_brief_prefix() -> None:
    state: PipelineState = {
        "brief_source": "# Client Brief: Acme Corp\n\nSome content here.",
        "errors": [],
    }
    result = intake(state)

    assert result["client_name"] == "Acme Corp"


# --- T-07: analyze_site node ---

from src.nodes.analyze_site import analyze_site


@patch("src.nodes.analyze_site.get_pages")
@patch("src.nodes.analyze_site.load_config")
def test_analyze_site_returns_pages(mock_config, mock_get_pages) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )
    mock_get_pages.return_value = [
        {"id": 1, "slug": "home", "title": "Home", "status": "publish"},
        {"id": 2, "slug": "about", "title": "About", "status": "draft"},
    ]

    state: PipelineState = {"errors": []}
    result = analyze_site(state)

    assert len(result["wp_existing_pages"]) == 2
    assert result["wp_existing_pages"][0]["slug"] == "home"
    assert result["errors"] == []


@patch("src.nodes.analyze_site.get_pages")
@patch("src.nodes.analyze_site.load_config")
def test_analyze_site_handles_unreachable_wp(mock_config, mock_get_pages) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )
    mock_get_pages.side_effect = ConnectionError("Connection refused")

    state: PipelineState = {"errors": []}
    result = analyze_site(state)

    assert result["wp_existing_pages"] == []
    assert any("unreachable" in e.lower() for e in result["errors"])


@patch("src.nodes.analyze_site.get_pages")
@patch("src.nodes.analyze_site.load_config")
def test_analyze_site_passes_credentials(mock_config, mock_get_pages) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://mysite.local",
        wp_username="editor",
        wp_app_password="secret-pass",
    )
    mock_get_pages.return_value = []

    state: PipelineState = {"errors": []}
    analyze_site(state)

    mock_get_pages.assert_called_once_with("https://mysite.local", "editor", "secret-pass")

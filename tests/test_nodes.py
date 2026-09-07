"""Tests for wired nodes: T-06 intake, T-07 analyze_site, T-08 generate, T-09 review."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.nodes.intake import intake
from src.state import PipelineState, Section

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


# --- T-08: generate node ---

from src.nodes.generate import generate

FAKE_SECTIONS: list[Section] = [
    {
        "title": "Home",
        "body": "<h1>Welcome</h1>",
        "meta_description": "Home page",
        "target_page": "home",
    },
    {
        "title": "About",
        "body": "<h1>About Us</h1>",
        "meta_description": "About page",
        "target_page": None,
    },
]


@patch("src.nodes.generate.generate_sections", return_value=FAKE_SECTIONS)
@patch("src.nodes.generate.load_config")
def test_generate_calls_with_brief_and_pages(mock_config, mock_gen) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )

    state: PipelineState = {
        "brief_content": "Build a site for Acme",
        "wp_existing_pages": [{"id": 1, "slug": "home", "title": "Home", "status": "publish"}],
        "generation_attempts": 0,
        "errors": [],
    }
    result = generate(state)

    mock_gen.assert_called_once_with(
        brief="Build a site for Acme",
        existing_pages=[{"id": 1, "slug": "home", "title": "Home", "status": "publish"}],
        feedback=None,
        api_key="sk-test",
    )
    assert result["sections"] == FAKE_SECTIONS


@patch("src.nodes.generate.generate_sections", return_value=FAKE_SECTIONS)
@patch("src.nodes.generate.load_config")
def test_generate_increments_attempts(mock_config, mock_gen) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )

    state: PipelineState = {
        "brief_content": "brief",
        "wp_existing_pages": [],
        "generation_attempts": 1,
        "errors": [],
    }
    result = generate(state)

    assert result["generation_attempts"] == 2


@patch("src.nodes.generate.generate_sections", return_value=FAKE_SECTIONS)
@patch("src.nodes.generate.load_config")
def test_generate_passes_feedback(mock_config, mock_gen) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )

    state: PipelineState = {
        "brief_content": "brief",
        "wp_existing_pages": [],
        "generation_attempts": 0,
        "generation_feedback": "Make it shorter",
        "errors": [],
    }
    generate(state)

    _, kwargs = mock_gen.call_args
    assert kwargs["feedback"] == "Make it shorter"


@patch("src.nodes.generate.generate_sections")
@patch("src.nodes.generate.load_config")
def test_generate_handles_api_failure(mock_config, mock_gen) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )
    mock_gen.side_effect = RuntimeError("API exploded")

    state: PipelineState = {
        "brief_content": "brief",
        "wp_existing_pages": [],
        "generation_attempts": 0,
        "errors": [],
    }
    result = generate(state)

    assert result["sections"] == []
    assert result["generation_attempts"] == 1
    assert any("generation failed" in e.lower() for e in result["errors"])


# --- T-09: review node ---

from src.nodes.review import review


def test_review_approve(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "a")

    state: PipelineState = {
        "client_name": "Acme Corp",
        "sections": FAKE_SECTIONS,
        "errors": [],
    }
    result = review(state)

    assert result["approval_status"] == "approved"


def test_review_reject_with_feedback(monkeypatch) -> None:
    inputs = iter(["r", "Make the headings punchier"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    state: PipelineState = {
        "client_name": "Acme Corp",
        "sections": FAKE_SECTIONS,
        "errors": [],
    }
    result = review(state)

    assert result["approval_status"] == "rejected"
    assert result["generation_feedback"] == "Make the headings punchier"


def test_review_quit(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "q")

    state: PipelineState = {
        "client_name": "Acme Corp",
        "sections": FAKE_SECTIONS,
        "errors": [],
    }
    result = review(state)

    assert result["approval_status"] == "rejected"
    assert result["generation_attempts"] == 3

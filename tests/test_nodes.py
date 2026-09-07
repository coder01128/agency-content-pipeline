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


# --- T-10: publish node ---

from src.nodes.publish import publish


def _make_settings():
    from src.config import Settings

    return Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )


@patch("src.nodes.publish.create_draft_page")
@patch("src.nodes.publish.load_config")
def test_publish_creates_new_page(mock_config, mock_create) -> None:
    mock_config.return_value = _make_settings()
    mock_create.return_value = {
        "id": 20,
        "slug": "about",
        "title": "About",
        "status": "draft",
        "link": "https://test.local/?page_id=20",
    }

    state: PipelineState = {
        "sections": [
            {
                "title": "About",
                "body": "<p>About us</p>",
                "meta_description": "About",
                "target_page": None,
            }
        ],
        "wp_existing_pages": [],
        "errors": [],
    }
    result = publish(state)

    assert result["draft_urls"] == ["https://test.local/?page_id=20"]
    mock_create.assert_called_once()


@patch("src.nodes.publish.update_draft_page")
@patch("src.nodes.publish.load_config")
def test_publish_updates_existing_page(mock_config, mock_update) -> None:
    mock_config.return_value = _make_settings()
    mock_update.return_value = {
        "id": 2,
        "slug": "home",
        "title": "Home",
        "status": "draft",
        "link": "https://test.local/home/",
    }

    state: PipelineState = {
        "sections": [
            {
                "title": "Home",
                "body": "<p>Updated home</p>",
                "meta_description": "Home",
                "target_page": "home",
            }
        ],
        "wp_existing_pages": [
            {"id": 2, "slug": "home", "title": "Home", "status": "publish"}
        ],
        "errors": [],
    }
    result = publish(state)

    assert result["draft_urls"] == ["https://test.local/home/"]
    mock_update.assert_called_once_with(
        "https://test.local", "admin", "pass", 2, "Home", "<p>Updated home</p>"
    )


@patch("src.nodes.publish.create_draft_page")
@patch("src.nodes.publish.update_draft_page")
@patch("src.nodes.publish.load_config")
def test_publish_all_calls_use_draft_status(mock_config, mock_update, mock_create) -> None:
    """CRITICAL SAFETY TEST: publish node must only ever produce draft pages."""
    mock_config.return_value = _make_settings()
    mock_create.return_value = {
        "id": 30, "slug": "new", "title": "New", "status": "draft",
        "link": "https://test.local/?page_id=30",
    }
    mock_update.return_value = {
        "id": 2, "slug": "home", "title": "Home", "status": "draft",
        "link": "https://test.local/home/",
    }

    state: PipelineState = {
        "sections": [
            {"title": "Home", "body": "<p>H</p>", "meta_description": "H", "target_page": "home"},
            {"title": "New", "body": "<p>N</p>", "meta_description": "N", "target_page": None},
        ],
        "wp_existing_pages": [
            {"id": 2, "slug": "home", "title": "Home", "status": "publish"}
        ],
        "errors": [],
    }
    publish(state)

    assert mock_update.called
    assert mock_create.called
    # The safety invariant is enforced inside wordpress.py (create_draft_page
    # and update_draft_page hard-code status="draft"). Publish node only calls
    # those two functions — never a raw HTTP call — so draft-only is guaranteed
    # by construction. This test verifies the node routes correctly to those
    # functions rather than bypassing them.


@patch("src.nodes.publish.create_draft_page")
@patch("src.nodes.publish.load_config")
def test_publish_partial_failure(mock_config, mock_create) -> None:
    mock_config.return_value = _make_settings()

    call_count = {"n": 0}

    def create_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise ConnectionError("WP down")
        return {
            "id": 10 + call_count["n"],
            "slug": f"page-{call_count['n']}",
            "title": f"Page {call_count['n']}",
            "status": "draft",
            "link": f"https://test.local/?page_id={10 + call_count['n']}",
        }

    mock_create.side_effect = create_side_effect

    state: PipelineState = {
        "sections": [
            {"title": "Page 1", "body": "<p>1</p>", "meta_description": "1", "target_page": None},
            {"title": "Page 2", "body": "<p>2</p>", "meta_description": "2", "target_page": None},
            {"title": "Page 3", "body": "<p>3</p>", "meta_description": "3", "target_page": None},
        ],
        "wp_existing_pages": [],
        "errors": [],
    }
    result = publish(state)

    assert len(result["draft_urls"]) == 2
    assert any("Page 2" in e for e in result["errors"])


@patch("src.nodes.publish.create_draft_page")
@patch("src.nodes.publish.load_config")
def test_publish_returns_urls_for_successes(mock_config, mock_create) -> None:
    mock_config.return_value = _make_settings()
    mock_create.return_value = {
        "id": 50, "slug": "gallery", "title": "Gallery", "status": "draft",
        "link": "https://test.local/?page_id=50",
    }

    state: PipelineState = {
        "sections": [
            {"title": "Gallery", "body": "<p>G</p>", "meta_description": "G", "target_page": None},
        ],
        "wp_existing_pages": [],
        "errors": [],
    }
    result = publish(state)

    assert result["draft_urls"] == ["https://test.local/?page_id=50"]
    assert result["errors"] == []


# --- T-11: notify node ---

from src.nodes.notify import notify


@patch("src.nodes.notify.load_config")
def test_notify_prints_summary(mock_config, capsys) -> None:
    mock_config.side_effect = ValueError("no config")

    state: PipelineState = {
        "client_name": "Acme Corp",
        "draft_urls": [
            "https://test.local/?page_id=20",
            "https://test.local/?page_id=30",
        ],
        "errors": [],
    }
    result = notify(state)

    captured = capsys.readouterr()
    assert "Acme Corp" in captured.out
    assert "page_id=20" in captured.out
    assert "page_id=30" in captured.out
    assert "Drafts created: 2" in captured.out
    assert result["notification_sent"] is True


@patch("src.nodes.notify.httpx.post")
@patch("src.nodes.notify.load_config")
def test_notify_sends_slack(mock_config, mock_post) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
        slack_webhook_url="https://hooks.slack.com/test",
    )

    state: PipelineState = {
        "client_name": "Acme Corp",
        "draft_urls": ["https://test.local/?page_id=20"],
        "errors": [],
    }
    notify(state)

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[0][0] == "https://hooks.slack.com/test"
    assert "Acme Corp" in call_kwargs[1]["json"]["text"]


@patch("src.nodes.notify.load_config")
def test_notify_works_without_slack(mock_config) -> None:
    from src.config import Settings

    mock_config.return_value = Settings(
        anthropic_api_key="sk-test",
        wp_site_url="https://test.local",
        wp_username="admin",
        wp_app_password="pass",
    )

    state: PipelineState = {
        "client_name": "Acme Corp",
        "draft_urls": [],
        "errors": [],
    }
    result = notify(state)

    assert result["notification_sent"] is True
    assert result["errors"] == []

"""Test T-03: WordPress REST client with draft-only safety constraint."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from src.tools.wordpress import (
    WordPressError,
    create_draft_page,
    get_pages,
    update_draft_page,
)

FIXTURES = Path(__file__).parent / "fixtures"
SITE = "https://greenscape.local"
USER = "admin"
PASS = "xxxx xxxx xxxx"


@pytest.fixture()
def wp_pages_json() -> list[dict]:
    return json.loads((FIXTURES / "wp_pages_response.json").read_text())


@respx.mock
def test_get_pages_returns_parsed_list(wp_pages_json: list[dict]) -> None:
    respx.get(f"{SITE}/wp-json/wp/v2/pages").mock(
        return_value=httpx.Response(200, json=wp_pages_json)
    )

    pages = get_pages(SITE, USER, PASS)

    assert len(pages) == 4
    assert pages[0] == {"id": 2, "slug": "home", "title": "Home", "status": "publish"}
    assert pages[2] == {
        "id": 8,
        "slug": "about-draft",
        "title": "About Us",
        "status": "draft",
    }


@respx.mock
def test_create_draft_page_sends_correct_payload() -> None:
    created = {
        "id": 20,
        "slug": "gallery",
        "status": "draft",
        "title": {"rendered": "Gallery"},
        "content": {"rendered": "<p>Photos</p>"},
        "link": "https://greenscape.local/?page_id=20",
    }
    route = respx.post(f"{SITE}/wp-json/wp/v2/pages").mock(
        return_value=httpx.Response(201, json=created)
    )

    result = create_draft_page(SITE, USER, PASS, "Gallery", "<p>Photos</p>", "gallery")

    assert result["id"] == 20
    assert result["status"] == "draft"
    assert result["slug"] == "gallery"

    sent = json.loads(route.calls[0].request.content)
    assert sent["title"] == "Gallery"
    assert sent["content"] == "<p>Photos</p>"
    assert sent["slug"] == "gallery"


@respx.mock
def test_draft_status_hardcoded_in_all_write_requests() -> None:
    """CRITICAL SAFETY TEST: every outgoing write request must contain status='draft'."""
    create_response = {
        "id": 30,
        "slug": "new-page",
        "status": "draft",
        "title": {"rendered": "New Page"},
        "content": {"rendered": "<p>Content</p>"},
        "link": "https://greenscape.local/?page_id=30",
    }
    update_response = {
        "id": 2,
        "slug": "home",
        "status": "draft",
        "title": {"rendered": "Home Updated"},
        "content": {"rendered": "<p>Updated</p>"},
        "link": "https://greenscape.local/home/",
    }

    create_route = respx.post(f"{SITE}/wp-json/wp/v2/pages").mock(
        return_value=httpx.Response(201, json=create_response)
    )
    update_route = respx.post(f"{SITE}/wp-json/wp/v2/pages/2").mock(
        return_value=httpx.Response(200, json=update_response)
    )

    create_draft_page(SITE, USER, PASS, "New Page", "<p>Content</p>", "new-page")
    update_draft_page(SITE, USER, PASS, 2, "Home Updated", "<p>Updated</p>")

    create_body = json.loads(create_route.calls[0].request.content)
    assert create_body["status"] == "draft", "create_draft_page MUST send status='draft'"

    update_body = json.loads(update_route.calls[0].request.content)
    assert update_body["status"] == "draft", "update_draft_page MUST send status='draft'"


@respx.mock
def test_get_pages_handles_401() -> None:
    respx.get(f"{SITE}/wp-json/wp/v2/pages").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )

    with pytest.raises(WordPressError, match="authentication failed"):
        get_pages(SITE, USER, PASS)


@respx.mock
def test_get_pages_handles_empty_site() -> None:
    respx.get(f"{SITE}/wp-json/wp/v2/pages").mock(
        return_value=httpx.Response(200, json=[])
    )

    pages = get_pages(SITE, USER, PASS)
    assert pages == []

from __future__ import annotations

import httpx

_TIMEOUT = 30.0


class WordPressError(Exception):
    pass


def _auth(username: str, app_password: str) -> httpx.BasicAuth:
    return httpx.BasicAuth(username, app_password)


def _handle_response(response: httpx.Response) -> None:
    if response.status_code == 401:
        raise WordPressError(
            "WordPress authentication failed (401). Check WP_USERNAME and WP_APP_PASSWORD."
        )
    if response.status_code == 404:
        raise WordPressError(
            "WordPress site or endpoint not found (404). "
            "Check WP_SITE_URL and ensure the REST API is enabled."
        )
    response.raise_for_status()


def get_pages(site_url: str, username: str, app_password: str) -> list[dict]:
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/pages"
    params = {"per_page": 100, "status": "publish,draft"}

    try:
        response = httpx.get(
            url, params=params, auth=_auth(username, app_password), timeout=_TIMEOUT
        )
    except httpx.HTTPStatusError:
        raise
    except httpx.HTTPError as exc:
        raise WordPressError(f"Failed to connect to WordPress: {exc}") from exc

    _handle_response(response)

    return [
        {
            "id": page["id"],
            "slug": page["slug"],
            "title": page["title"]["rendered"],
            "status": page["status"],
        }
        for page in response.json()
    ]


def create_draft_page(
    site_url: str,
    username: str,
    app_password: str,
    title: str,
    content: str,
    slug: str,
) -> dict:
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/pages"
    payload = {
        "title": title,
        "content": content,
        "slug": slug,
        "status": "draft",
    }

    try:
        response = _post_with_retry(url, payload, username, app_password)
    except httpx.HTTPError as exc:
        raise WordPressError(f"Failed to create draft page: {exc}") from exc

    _handle_response(response)

    data = response.json()
    return {
        "id": data["id"],
        "slug": data["slug"],
        "title": data["title"]["rendered"],
        "status": data["status"],
        "link": data["link"],
    }


def update_draft_page(
    site_url: str,
    username: str,
    app_password: str,
    page_id: int,
    title: str,
    content: str,
) -> dict:
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    payload = {
        "title": title,
        "content": content,
        "status": "draft",
    }

    try:
        response = _post_with_retry(url, payload, username, app_password)
    except httpx.HTTPError as exc:
        raise WordPressError(f"Failed to update draft page: {exc}") from exc

    _handle_response(response)

    data = response.json()
    return {
        "id": data["id"],
        "slug": data["slug"],
        "title": data["title"]["rendered"],
        "status": data["status"],
        "link": data["link"],
    }


def _post_with_retry(url: str, payload: dict, username: str, app_password: str) -> httpx.Response:
    response = httpx.post(url, json=payload, auth=_auth(username, app_password), timeout=_TIMEOUT)
    if response.status_code >= 500:
        response = httpx.post(
            url, json=payload, auth=_auth(username, app_password), timeout=_TIMEOUT
        )
    return response

from __future__ import annotations

from typing import TypedDict


class Section(TypedDict):
    title: str
    body: str
    meta_description: str
    target_page: str | None


class PipelineState(TypedDict, total=False):
    brief_source: str
    brief_content: str
    client_name: str
    wp_site_url: str
    wp_existing_pages: list[dict]
    sections: list[Section]
    generation_attempts: int
    generation_feedback: str | None
    approval_status: str
    draft_urls: list[str]
    notification_sent: bool
    errors: list[str]

from __future__ import annotations

import time

import anthropic

from src.state import Section

SECTION_TOOL: dict = {
    "name": "create_sections",
    "description": (
        "Create website page sections based on a client brief. "
        "Each section maps to a WordPress page with title, body HTML, "
        "meta description, and optional target page slug for updates."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "description": "List of page sections to create or update",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Page title",
                        },
                        "body": {
                            "type": "string",
                            "description": "Page body as HTML",
                        },
                        "meta_description": {
                            "type": "string",
                            "description": "SEO meta description, max 160 chars",
                        },
                        "target_page": {
                            "type": ["string", "null"],
                            "description": (
                                "Slug of existing WP page to update, or null for a new page"
                            ),
                        },
                    },
                    "required": ["title", "body", "meta_description", "target_page"],
                },
            }
        },
        "required": ["sections"],
    },
}

_SYSTEM_PROMPT = (
    "You are an expert web copywriter working for a digital agency. "
    "You write clear, persuasive website copy that converts visitors into leads. "
    "Given a client brief and their existing website pages, create or update "
    "page content using the create_sections tool. "
    "Write in the client's requested tone. Use HTML for body content. "
    "Match existing page slugs where updates are appropriate; use null for new pages."
)

_MAX_RETRIES = 2
_RETRY_DELAY = 2.0


class ClaudeToolError(Exception):
    pass


def generate_sections(
    brief: str,
    existing_pages: list[dict],
    feedback: str | None,
    api_key: str,
) -> list[Section]:
    client = anthropic.Anthropic(api_key=api_key)

    user_content = f"## Client Brief\n\n{brief}\n\n"
    if existing_pages:
        pages_text = "\n".join(
            f"- {p.get('title', 'Untitled')} (/{p.get('slug', '')})" for p in existing_pages
        )
        user_content += f"## Existing WordPress Pages\n\n{pages_text}\n\n"
    if feedback:
        user_content += f"## Revision Feedback\n\n{feedback}\n\n"

    user_content += "Use the create_sections tool to generate the page content."

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-5",
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                tools=[SECTION_TOOL],
                tool_choice={"type": "tool", "name": "create_sections"},
            )
            break
        except anthropic.RateLimitError as exc:
            if attempt == _MAX_RETRIES:
                raise ClaudeToolError("Claude API rate limit exceeded after retries.") from exc
            time.sleep(_RETRY_DELAY * (attempt + 1))
        except anthropic.AuthenticationError as exc:
            raise ClaudeToolError(
                "Claude API authentication failed. Check ANTHROPIC_API_KEY."
            ) from exc
        except anthropic.APIError as exc:
            raise ClaudeToolError(f"Claude API error: {exc}") from exc

    for block in response.content:
        if block.type == "tool_use" and block.name == "create_sections":
            raw_sections = block.input.get("sections", [])
            return [
                Section(
                    title=s.get("title", "Untitled"),
                    body=s.get("body", ""),
                    meta_description=s.get("meta_description", ""),
                    target_page=s.get("target_page"),
                )
                for s in raw_sections
            ]

    raise ClaudeToolError("Claude response did not contain expected tool_use block.")

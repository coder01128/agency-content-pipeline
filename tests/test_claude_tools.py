"""Test T-04: Claude tool use integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.state import Section
from src.tools.claude_tools import (
    SECTION_TOOL,
    ClaudeToolError,
    generate_sections,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture() -> dict:
    return json.loads((FIXTURES / "claude_tool_response.json").read_text())


def _mock_response_from_fixture():
    """Build a mock that mimics anthropic Message with .content[].type/name/input."""
    fixture = _load_fixture()
    blocks = []
    for block_data in fixture["content"]:
        block = MagicMock()
        block.type = block_data["type"]
        block.name = block_data.get("name")
        block.input = block_data.get("input", {})
        blocks.append(block)

    response = MagicMock()
    response.content = blocks
    response.stop_reason = fixture["stop_reason"]
    return response


@patch("src.tools.claude_tools.anthropic.Anthropic")
def test_sends_correct_tool_definition(mock_anthropic_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response_from_fixture()

    generate_sections("Test brief", [], None, "sk-test-key")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tools"] == [SECTION_TOOL]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "create_sections"}
    assert call_kwargs["model"] == "claude-sonnet-5"


@patch("src.tools.claude_tools.anthropic.Anthropic")
def test_parses_tool_response_into_sections(mock_anthropic_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response_from_fixture()

    sections = generate_sections("Test brief", [], None, "sk-test-key")

    assert len(sections) == 3
    assert sections[0]["title"] == "Home"
    assert sections[0]["target_page"] == "home"
    assert sections[1]["target_page"] is None
    assert "GreenScape" in sections[0]["body"]
    assert len(sections[0]["meta_description"]) > 0


@patch("src.tools.claude_tools.anthropic.Anthropic")
def test_includes_feedback_in_prompt(mock_anthropic_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response_from_fixture()

    existing = [{"title": "Home", "slug": "home"}]
    generate_sections("Brief text", existing, "Make it shorter", "sk-test-key")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    user_msg = call_kwargs["messages"][0]["content"]
    assert "Make it shorter" in user_msg
    assert "Revision Feedback" in user_msg
    assert "Home (/home)" in user_msg


@patch("src.tools.claude_tools.anthropic.Anthropic")
def test_handles_api_error(mock_anthropic_cls: MagicMock) -> None:
    import anthropic

    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.side_effect = anthropic.APIError(
        message="Server error",
        request=MagicMock(),
        body=None,
    )

    with pytest.raises(ClaudeToolError, match="Claude API error"):
        generate_sections("Brief", [], None, "sk-test-key")


def test_tool_schema_matches_section_fields() -> None:
    section_fields = set(Section.__annotations__.keys())
    schema_props = set(
        SECTION_TOOL["input_schema"]["properties"]["sections"]["items"]["properties"].keys()
    )
    assert schema_props == section_fields

    required = set(SECTION_TOOL["input_schema"]["properties"]["sections"]["items"]["required"])
    assert required == section_fields

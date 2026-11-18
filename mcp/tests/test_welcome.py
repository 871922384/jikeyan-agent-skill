"""First-conversation coverage: instructions, welcome prompt, fallback path.

Uses fake HTTP transports only; no network.
"""

from __future__ import annotations

import httpx
import pytest

from jikeyan_mcp.config import Config
from jikeyan_mcp.prompts import (
    WELCOME_FALLBACK_PATH,
    WELCOME_PROMPT_DESCRIPTION,
    WELCOME_PROMPT_NAME,
    welcome_prompt_text,
)
from jikeyan_mcp.server import _instructions, build_server


def test_welcome_prompt_text_covers_the_flow() -> None:
    text = welcome_prompt_text()
    assert "get_schema" in text and "get_today" in text and "list_projects" in text
    assert "welcome" in text  # schema.welcome preferred, bundled copy is fallback
    assert WELCOME_FALLBACK_PATH in text
    assert "{project_count}" in text and "{overdue_count}" in text
    assert "{waiting_today_count}" in text
    assert "opening_empty" in text and "suggestions" in text and "tone" in text


def test_server_instructions_mention_the_greeting() -> None:
    instructions = _instructions()
    assert "第一次对话" in instructions
    assert WELCOME_PROMPT_NAME in instructions


@pytest.mark.asyncio
async def test_server_registers_jikeyan_welcome_prompt() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    server = build_server(
        Config(base_url="https://api.jikeyan.cn", agent_key="jk_test_placeholder"),
        transport=httpx.MockTransport(handler),
    )
    prompt = await server.get_prompt(WELCOME_PROMPT_NAME)
    assert prompt is not None
    assert prompt.description == WELCOME_PROMPT_DESCRIPTION
    result = await prompt.render()
    bodies = [
        getattr(message.content, "text", "")
        for message in result.messages
        if getattr(message, "content", None) is not None
    ]
    assert welcome_prompt_text() in "\n".join(bodies)

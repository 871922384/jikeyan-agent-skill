"""First-conversation coverage: instructions, welcome prompt, fallback path.

Uses fake HTTP transports only; no network.
"""

from __future__ import annotations

from pathlib import Path

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

REPO_ROOT = Path(__file__).resolve().parents[2]

ZH = {
    "opening": "你好，我已经接手你的极科研看板，改动会同步到你的手机上。目前手头有 {project_count} 个项目，其中 {overdue_count} 项已经逾期、需要优先处理，今天还有 {waiting_today_count} 件在等的事该问一下了。今天我们先从哪一项开始推进？",
    "opening_no_overdue": "你好，我已经接手你的极科研看板，改动会同步到你的手机上。目前手头有 {project_count} 个项目，都没有逾期，不过今天有 {waiting_today_count} 件在等的事该问一下了。今天我们先从哪一项开始推进？",
    "opening_no_waiting": "你好，我已经接手你的极科研看板，改动会同步到你的手机上。目前手头有 {project_count} 个项目，其中 {overdue_count} 项已经逾期、需要优先处理。今天我们先从哪一项开始推进？",
    "opening_clear": "你好，我已经接手你的极科研看板，改动会同步到你的手机上。目前手头有 {project_count} 个项目，都在正轨上，没有逾期也没有需要催问的事。今天你想推进点什么？",
}

EN = {
    "opening": "Hi! I've taken over your Jikeyan project board, and every change will show up on your phone. You have {project_count} active projects, {overdue_count} of them overdue and worth tackling first, plus {waiting_today_count} waiting items due for a follow-up today. Where should we start?",
    "opening_no_overdue": "Hi! I've taken over your Jikeyan project board, and every change will show up on your phone. You have {project_count} active projects and none are overdue, but there are {waiting_today_count} waiting items due for a follow-up today. Where should we start?",
    "opening_no_waiting": "Hi! I've taken over your Jikeyan project board, and every change will show up on your phone. You have {project_count} active projects, {overdue_count} of them overdue and worth tackling first. Where should we start?",
    "opening_clear": "Hi! I've taken over your Jikeyan project board, and every change will show up on your phone. You have {project_count} active projects and everything is on track, with nothing overdue or waiting on follow-up. What would you like to work on today?",
}

EXPECTED_PLACEHOLDERS = {
    "opening": {"{project_count}", "{overdue_count}", "{waiting_today_count}"},
    "opening_no_overdue": {"{project_count}", "{waiting_today_count}"},
    "opening_no_waiting": {"{project_count}", "{overdue_count}"},
    "opening_clear": {"{project_count}"},
}


def test_welcome_prompt_text_covers_the_flow() -> None:
    text = welcome_prompt_text()
    assert "get_schema" in text and "get_today" in text and "list_projects" in text
    assert "welcome" in text  # schema.welcome preferred, bundled copy is fallback
    assert WELCOME_FALLBACK_PATH in text
    assert "{project_count}" in text and "{overdue_count}" in text
    assert "{waiting_today_count}" in text
    for variant in ("opening", "opening_empty", "opening_no_overdue",
                    "opening_no_waiting", "opening_clear"):
        assert variant in text
    assert "suggestions" in text and "tone" in text


def test_fallback_copy_matches_approved_variants() -> None:
    text = (REPO_ROOT / WELCOME_FALLBACK_PATH).read_text(encoding="utf-8")
    for variants in (ZH, EN):
        for key, copy in variants.items():
            assert copy in text, key
    # No variant may hardcode a zero count ("0 项"); the 5-way rule
    # picks a variant so zero counts never need to be read aloud.
    assert "0 项" not in text


def test_fallback_variants_carry_expected_placeholders() -> None:
    text = (REPO_ROOT / WELCOME_FALLBACK_PATH).read_text(encoding="utf-8")
    for key, placeholders in EXPECTED_PLACEHOLDERS.items():
        for variants in (ZH, EN):
            copy = variants[key]
            assert copy in text, key
            for ph in placeholders:
                assert ph in copy, (key, ph)


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

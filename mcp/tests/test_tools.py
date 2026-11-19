"""Tool inventory, annotations, privacy notice, and write-path wiring.

Uses fake HTTP transports only. FastMCP server machinery itself is not
exercised beyond construction (no network at build time).
"""

from __future__ import annotations

import httpx
import pytest

from jikeyan_mcp.client import AgentApiClient
from jikeyan_mcp.schema import PRIVACY_NOTICE
from jikeyan_mcp.tools import (
    ALL_TOOLS,
    READ_TOOL_NAMES,
    ToolContext,
    privacy_suffix,
    tool_annotations,
)

EXPECTED_TOOLS = [
    "get_today",
    "list_projects",
    "get_project",
    "get_changes",
    "get_schema",
    "verify_references",
    "check_topic_collision",
    "create_project",
    "update_project",
    "upsert_node",
    "complete_node",
    "upsert_waiting_item",
    "complete_waiting_item",
    "upsert_submission",
    "add_review_round",
    "append_timeline",
    "archive_project",
]


def test_tool_inventory_matches_documented_surface() -> None:
    assert [tool.__name__ for tool in ALL_TOOLS] == EXPECTED_TOOLS


def test_every_tool_has_a_docstring_and_a_privacy_suffix() -> None:
    assert privacy_suffix() == PRIVACY_NOTICE
    assert "患者" in PRIVACY_NOTICE  # compliance sentence must survive refactors
    for tool in ALL_TOOLS:
        assert tool.__doc__, tool.__name__


def test_annotations_mark_reads_and_destructive_writes() -> None:
    for name in READ_TOOL_NAMES:
        annotations = tool_annotations(name)
        assert annotations["readOnlyHint"] is True
        assert annotations["destructiveHint"] is False
    assert tool_annotations("archive_project")["destructiveHint"] is True
    assert tool_annotations("upsert_node")["readOnlyHint"] is False


def _context(handler, version: int = 3) -> tuple[ToolContext, list[httpx.Request]]:
    recorded: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return handler(request)

    client = AgentApiClient(
        base_url="https://api.jikeyan.cn",
        agent_key="jk_test_placeholder",
        transport=httpx.MockTransport(wrapped),
    )
    return ToolContext(client), recorded


@pytest.mark.asyncio
async def test_resolve_version_reads_project_first() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"project": {"version": 7}})

    context, recorded = _context(handler)
    assert await context.resolve_version("proj_1") == 7
    assert recorded[0].url.path == "/api/v1/agent/projects/proj_1"
    await context.client.aclose()


@pytest.mark.asyncio
async def test_apply_operations_sends_base_version_and_dry_run() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"project": {"version": 2}})
        assert request.method == "PATCH"
        assert request.url.params.get("dry_run") == "true"
        return httpx.Response(200, json={"snapshot": {"version": 3}, "dry_run": True})

    context, recorded = _context(handler)
    result = await context.apply_operations(
        "proj_1",
        tool="update_project",
        base_version=None,  # omitted -> resolves the current version via GET
        changed_fields={"title": "t"},
        dry_run=True,
    )
    assert result["dry_run"] is True
    patch = recorded[-1]
    assert patch.method == "PATCH"
    await context.client.aclose()


def test_build_server_constructs_without_network() -> None:
    from jikeyan_mcp.config import Config
    from jikeyan_mcp.server import build_server

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    server = build_server(
        Config(base_url="https://api.jikeyan.cn", agent_key="jk_test_placeholder"),
        transport=httpx.MockTransport(handler),
    )
    assert server is not None

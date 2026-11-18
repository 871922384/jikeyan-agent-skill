"""HTTP client behaviour against fake transports. No real network."""

from __future__ import annotations

import json

import httpx
import pytest

from jikeyan_mcp.client import AgentApiClient, AgentApiError, AgentApiTransportError


def _client(handler) -> AgentApiClient:
    return AgentApiClient(
        base_url="https://api.jikeyan.cn",
        agent_key="jk_test_placeholder",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_error_envelope_is_passed_through_verbatim() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer jk_test_placeholder"
        return httpx.Response(
            422,
            json={
                "code": "HTTP_ERROR",
                "detail": "invalid_stage",
                "hint": "fix it",
                "details": {"allowed": ["idea"]},
            },
        )

    client = _client(handler)
    with pytest.raises(AgentApiError) as excinfo:
        await client.request("GET", "/api/v1/agent/schema", tool="get_schema")
    payload = excinfo.value.to_payload()
    assert payload["detail"] == "invalid_stage"
    assert payload["status_code"] == 422
    assert payload["details"] == {"allowed": ["idea"]}
    assert payload["hint"] == "fix it"
    await client.aclose()


@pytest.mark.asyncio
async def test_transport_failure_maps_to_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    client = _client(handler)
    with pytest.raises(AgentApiTransportError):
        await client.request("GET", "/api/v1/agent/today", tool="get_today")
    await client.aclose()


@pytest.mark.asyncio
async def test_success_returns_decoded_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    client = _client(handler)
    assert await client.request("GET", "/api/v1/agent/projects", tool="list_projects") == {
        "items": []
    }
    await client.aclose()


def test_dumps_is_deterministic_json() -> None:
    from jikeyan_mcp.client import dumps

    payload = {"code": "HTTP_ERROR", "detail": "x"}
    assert json.loads(dumps(payload)) == payload

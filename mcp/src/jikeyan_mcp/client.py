"""HTTP access to the existing ``/api/v1/agent/*`` API.

The MCP server never imports the FastAPI app, its services or its models: it
speaks plain HTTP to the public agent API and authenticates with the Agent
Key exactly like any other external agent would.

Nothing is persisted to disk. Logging is limited to the tool name and the
HTTP status code; request bodies, response bodies and the Agent Key are never
written to the log.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("jikeyan_mcp.client")

DEFAULT_TIMEOUT_SECONDS = 30.0


class AgentApiError(RuntimeError):
    """A non-2xx response from the agent API.

    ``code`` / ``detail`` / ``hint`` / ``details`` are copied verbatim from
    the server error envelope so the agent can repair its own call.
    """

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        detail: str,
        hint: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(f"{code}: {detail}")
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.hint = hint
        self.details = details

    def to_payload(self) -> dict[str, Any]:
        """Return the server error envelope, unchanged, plus the status code."""
        payload: dict[str, Any] = {
            "code": self.code,
            "detail": self.detail,
            "status_code": self.status_code,
        }
        if self.details is not None:
            payload["details"] = self.details
        if self.hint:
            payload["hint"] = self.hint
        return payload


class AgentApiTransportError(RuntimeError):
    """The agent API could not be reached at all."""


class AgentApiClient:
    """Thin async HTTP client bound to one Agent Key."""

    def __init__(
        self,
        *,
        base_url: str,
        agent_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"Authorization": f"Bearer {agent_key}"},
        )

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        tool: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Call the agent API and return the decoded JSON body.

        Raises :class:`AgentApiError` for any 4xx/5xx response and
        :class:`AgentApiTransportError` when the request never reached the
        server.
        """
        try:
            response = await self._client.request(
                method,
                path,
                params=params,
                json=body,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            logger.warning("mcp tool %s transport error: %s", tool, type(exc).__name__)
            raise AgentApiTransportError(
                f"调用极科研 API 失败：{type(exc).__name__}。请检查网络与 {path} 地址。"
            ) from exc

        logger.info("mcp tool %s -> %s", tool, response.status_code)
        if response.status_code >= 400:
            raise _error_from_response(response)
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}


def _error_from_response(response: httpx.Response) -> AgentApiError:
    """Turn the server error envelope into an :class:`AgentApiError`."""
    code = "HTTP_ERROR"
    detail = f"http_{response.status_code}"
    hint: str | None = None
    details: Any = None
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        raw_code = payload.get("code")
        if isinstance(raw_code, str) and raw_code:
            code = raw_code
        raw_detail = payload.get("detail")
        if isinstance(raw_detail, str) and raw_detail:
            detail = raw_detail
        raw_hint = payload.get("hint")
        if isinstance(raw_hint, str) and raw_hint:
            hint = raw_hint
        if "details" in payload:
            details = payload["details"]
    return AgentApiError(
        status_code=response.status_code,
        code=code,
        detail=detail,
        hint=hint,
        details=details,
    )


def dumps(payload: Any) -> str:
    """Serialize an error payload for the MCP error channel."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)

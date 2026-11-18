"""Build and run the FastMCP server.

The server is a *local* stdio process: it speaks HTTP to the public agent API
and never touches the database or the FastAPI application internals.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Sequence

import httpx
from fastmcp import FastMCP
from fastmcp.tools.base import Tool

from jikeyan_mcp import __version__
from jikeyan_mcp.client import AgentApiClient
from jikeyan_mcp.config import Config
from jikeyan_mcp.descriptions import apply_schema
from jikeyan_mcp.schema import AgentSchema
from jikeyan_mcp.tools import (
    ALL_TOOLS,
    CONTEXT_KEY,
    ToolContext,
    privacy_suffix,
    tool_annotations,
)

logger = logging.getLogger("jikeyan_mcp")

SERVER_NAME = "jikeyan"


def _instructions() -> str:
    return (
        "极科研课题管理工具。每个工具对应一组意图，而不是一条 REST 路径。\n"
        "建议顺序：先 get_schema 取枚举与长度上限，再 list_projects / get_project 读现状，\n"
        "再 upsert_node / upsert_waiting_item 写，最后 get_today 看今天。\n"
        f"{privacy_suffix()}\n"
        "服务端错误会带 code / detail / hint；请按 hint 自行修正后重试一次。"
    )


class JikeyanMCP(FastMCP):
    """A FastMCP server that keeps the tool metadata in sync with the API.

    The enum values and field length limits shown in the tool descriptions come
    from ``GET /agent/schema``. They are fetched when the server starts and
    refreshed on every ``tools/list`` until the fetch succeeds, so the agent
    never sees a stale or half-written contract.
    """

    def __init__(self, *args: Any, context: ToolContext, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._context = context
        self._schema: AgentSchema | None = None
        self._schema_applied = False

    async def load_schema(self) -> AgentSchema | None:
        """Fetch ``GET /agent/schema`` and bind it to the tool metadata."""
        try:
            payload = await self._context.get("/api/v1/agent/schema", tool="get_schema")
        except Exception as exc:
            logger.warning("could not load agent schema: %s", type(exc).__name__)
            return None
        if not isinstance(payload, dict):
            logger.warning("agent schema payload was not an object")
            return None
        schema = AgentSchema.from_payload(payload)
        self._context.set_schema(schema)
        self._schema = schema
        return schema

    async def list_tools(self, *, run_middleware: bool = True) -> Sequence[Tool]:
        tools = list(await super().list_tools(run_middleware=run_middleware))
        if not self._schema_applied:
            schema = await self.load_schema()
            if schema is not None:
                await apply_schema(self, schema, tools)
                self._schema_applied = True
        return tools


def build_server(
    config: Config,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    client: httpx.AsyncClient | None = None,
) -> FastMCP:
    """Create the MCP server for one configuration.

    ``transport`` and ``client`` exist for the tests: they let the suite point
    the server at an in-process ASGI app instead of the network.
    """
    api_client = AgentApiClient(
        base_url=config.base_url,
        agent_key=config.agent_key,
        transport=transport,
        client=client,
    )
    context = ToolContext(api_client)

    @asynccontextmanager
    async def lifespan(server: FastMCP):
        try:
            yield {CONTEXT_KEY: context}
        finally:
            await api_client.aclose()

    server = JikeyanMCP(
        SERVER_NAME,
        instructions=_instructions(),
        version=__version__,
        lifespan=lifespan,
        context=context,
    )

    for tool in ALL_TOOLS:
        server.tool(
            tool,
            name=tool.__name__,
            description=f"{tool.__doc__ or ''}\n\n{privacy_suffix()}",
            annotations=tool_annotations(tool.__name__),
        )
    return server


def run() -> None:
    """Entry point of ``python -m jikeyan_mcp`` and the ``jikeyan-mcp`` command."""
    from jikeyan_mcp.config import ConfigError, load_config

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # httpx logs the full request URL at INFO level, which contains project
    # ids. The MCP server only ever logs a tool name and a status code.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    try:
        config = load_config()
    except ConfigError as exc:
        # Startup error: write it to stderr and exit non-zero. The key is never
        # part of the message.
        raise SystemExit(f"极科研 MCP 服务启动失败：{exc}") from exc

    server = build_server(config)
    server.run(transport="stdio", show_banner=False)

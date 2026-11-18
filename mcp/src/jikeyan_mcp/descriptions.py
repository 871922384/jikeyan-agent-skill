"""Bind the runtime agent schema to the MCP tool metadata.

The numbers that matter (enum values, field length limits) live on the server.
They are fetched once at start-up from ``GET /agent/schema`` and written into
the tool descriptions and JSON schemas, so there is exactly one source of
truth: no second copy of "300" or "paused" anywhere in this package.
"""

from __future__ import annotations

from typing import Any

from jikeyan_mcp.schema import AgentSchema

#: Which tool parameter gets which enum from the agent schema.
ENUM_BINDINGS: dict[tuple[str, str], str] = {
    ("upsert_node", "kind"): "node_kinds",
    ("append_timeline", "kind"): "node_kinds",
    ("upsert_submission", "status"): "submission_statuses",
    ("upsert_waiting_item", "status"): "waiting_item_statuses",
}

#: Which tool parameter gets which length limit from the agent schema.
LIMIT_BINDINGS: dict[tuple[str, str], str] = {
    ("create_project", "title"): "title",
    ("update_project", "title"): "title",
    ("update_project", "status_note"): "status_note",
    ("create_project", "status_note"): "status_note",
    ("create_project", "external_ref"): "external_ref",
    ("upsert_node", "title"): "title",
    ("upsert_node", "detail"): "node_detail",
    ("upsert_node", "assignee_label"): "assignee_label",
    ("upsert_waiting_item", "title"): "title",
    ("upsert_waiting_item", "blocked_by_label"): "assignee_label",
    ("add_review_round", "comments_markdown"): "review_comments",
}


def _enum_values(schema: AgentSchema, key: str) -> list[str]:
    if key == "node_kinds":
        return list(schema.node_kinds)
    if key == "submission_statuses":
        return list(schema.submission_statuses)
    if key == "waiting_item_statuses":
        return list(schema.waiting_item_statuses)
    return []


def _limit_value(schema: AgentSchema, key: str) -> int | None:
    if key == "review_comments":
        # The review round columns are 10000 characters on the server.
        return 10000
    value = schema.limits.get(key)
    return int(value) if isinstance(value, int) else None


def description_suffix(schema: AgentSchema, tool_name: str) -> str:
    """The generated part of a tool description.

    It is appended to the hand-written sentence so the reader first learns what
    the tool does and then sees the exact contract.
    """
    lines: list[str] = []
    if tool_name in ("create_project", "update_project", "upsert_node"):
        lines.append(schema.templates_text())
    if tool_name in ("upsert_node", "append_timeline", "complete_node"):
        lines.append(schema.enums_text())
    if tool_name in ("upsert_waiting_item", "complete_waiting_item"):
        lines.append("等待项 status：" + ", ".join(schema.waiting_item_statuses) + "。")
    if tool_name == "upsert_submission":
        lines.append("投稿 status：" + ", ".join(schema.submission_statuses) + "。")
    if tool_name in ("upsert_node", "complete_node"):
        node_fields = schema.node_fields_text()
        if node_fields:
            lines.append(node_fields)
    limits_text = schema.limits_text()
    if limits_text:
        lines.append("字段长度上限：" + limits_text + "。")
    if tool_name == "get_schema":
        lines.append("返回内容与服务端同一来源，包含 templates / node_kinds / limits。")
    return "\n".join(lines)


async def apply_schema(server: Any, schema: AgentSchema, tools: list[Any]) -> None:
    """Write the fetched schema into the registered tools."""
    for tool in tools:
        name = tool.name
        suffix = description_suffix(schema, name)
        if suffix:
            tool.description = f"{tool.description}\n\n{suffix}"
        parameters = tool.parameters or {}
        properties = parameters.get("properties") or {}
        for (bound_tool, parameter), enum_key in ENUM_BINDINGS.items():
            if bound_tool != name or parameter not in properties:
                continue
            values = _enum_values(schema, enum_key)
            if values:
                properties[parameter]["enum"] = values
        for (bound_tool, parameter), limit_key in LIMIT_BINDINGS.items():
            if bound_tool != name or parameter not in properties:
                continue
            limit = _limit_value(schema, limit_key)
            if limit:
                properties[parameter]["maxLength"] = limit
        if properties:
            tool.parameters = {**parameters, "properties": properties}

"""The machine-readable contract of the agent API, fetched at runtime.

Everything that could drift (enum values, field length limits, allowed
operation fields) is taken from ``GET /agent/schema``. Nothing here repeats a
number that also exists on the server: the descriptions are *generated* from
the fetched payload, so the two cannot diverge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Never send these through the API. This is a server-side rule; the MCP
#: layer does not relax it.
PRIVACY_NOTICE = (
    "不要传患者姓名、住院号、诊断或随访文本；服务端不接受这些字段，"
    "只写课题、节点、等待项、投稿、审稿轮次与进展。"
)


@dataclass(frozen=True)
class AgentSchema:
    """The subset of ``GET /agent/schema`` the tool layer needs."""

    templates: dict[str, dict[str, Any]] = field(default_factory=dict)
    node_kinds: list[str] = field(default_factory=list)
    submission_statuses: list[str] = field(default_factory=list)
    waiting_item_statuses: list[str] = field(default_factory=list)
    operations: dict[str, list[str]] = field(default_factory=dict)
    limits: dict[str, int] = field(default_factory=dict)
    guide_markdown: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> AgentSchema:
        templates = payload.get("templates")
        operations = payload.get("operations")
        limits = payload.get("limits")
        return cls(
            templates=dict(templates) if isinstance(templates, dict) else {},
            node_kinds=list(payload.get("node_kinds") or []),
            submission_statuses=list(payload.get("submission_statuses") or []),
            waiting_item_statuses=list(payload.get("waiting_item_statuses") or []),
            operations=dict(operations) if isinstance(operations, dict) else {},
            limits={key: int(value) for key, value in (limits or {}).items()},
            guide_markdown=str(payload.get("guide_markdown") or ""),
            raw=payload,
        )

    # -- generated description fragments -----------------------------------

    def template_ids(self) -> list[str]:
        return list(self.templates)

    def limit(self, name: str, default: int = 0) -> int:
        return int(self.limits.get(name, default))

    def templates_text(self) -> str:
        if not self.templates:
            return "课题类型未知，请先调用 get_schema。"
        parts = []
        for template_id, info in self.templates.items():
            name = info.get("name") or template_id
            stages = ", ".join(info.get("stages") or [])
            parts.append(f"{template_id}（{name}）阶段：{stages}")
        return "\n".join(parts)

    def stages_text(self) -> str:
        return self.templates_text()

    def enums_text(self) -> str:
        return (
            f"节点 kind：{', '.join(self.node_kinds)}。\n"
            f"投稿 status：{', '.join(self.submission_statuses)}。\n"
            f"等待项 status：{', '.join(self.waiting_item_statuses)}。"
        )

    def limits_text(self) -> str:
        if not self.limits:
            return "字段长度上限未知，请先调用 get_schema。"
        return "；".join(f"{key} ≤ {value}" for key, value in sorted(self.limits.items()))

    def node_fields_text(self) -> str:
        allowed = self.operations.get("upsert_node") or []
        if not allowed:
            return ""
        return "节点可写字段：" + ", ".join(allowed) + "。"

    def operation_fields_text(self, action: str) -> str:
        allowed = self.operations.get(action) or []
        if not allowed:
            return ""
        return f"{action} 可写字段：" + ", ".join(allowed) + "。"

    def summary(self) -> dict[str, Any]:
        """The payload returned by the ``get_schema`` tool."""
        return {
            "templates": self.templates,
            "node_kinds": self.node_kinds,
            "submission_statuses": self.submission_statuses,
            "waiting_item_statuses": self.waiting_item_statuses,
            "operations": self.operations,
            "limits": self.limits,
        }

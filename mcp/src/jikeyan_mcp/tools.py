"""The MCP tools.

Project tools wrap the existing ``/api/v1/agent/*`` HTTP API;
verify_references queries public metadata providers from the local process. There is no database access and no import of the
FastAPI application: the only coupling is the public HTTP contract.

Tool count is deliberately kept small (17) so an agent picks the right tool.
"""

from __future__ import annotations

import json
import asyncio
import os

from jikeyan_mcp.local_search import references
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context

from jikeyan_mcp.client import AgentApiClient, AgentApiError, AgentApiTransportError
from jikeyan_mcp.schema import PRIVACY_NOTICE, AgentSchema

#: Where the write tools live, relative to the API root.
PROJECTS_PATH = "/api/v1/agent/projects"

#: Key under which the tool context is published in the lifespan context.
CONTEXT_KEY = "jikeyan_tool_context"


class ToolContext:
    """Shared state for the tool functions."""

    def __init__(self, client: AgentApiClient) -> None:
        self.client = client
        self._schema: AgentSchema | None = None

    @property
    def schema(self) -> AgentSchema:
        if self._schema is None:
            raise ToolError(
                json.dumps(
                    {
                        "code": "SCHEMA_UNAVAILABLE",
                        "detail": "agent_schema_not_loaded",
                        "hint": "MCP 服务尚未拉取 GET /agent/schema，请重试一次。",
                    },
                    ensure_ascii=False,
                )
            )
        return self._schema

    def set_schema(self, schema: AgentSchema) -> None:
        self._schema = schema

    # -- request helpers ---------------------------------------------------

    async def get(self, path: str, *, tool: str, params: dict[str, Any] | None = None) -> Any:
        return await self._call("GET", path, tool=tool, params=params)

    async def post(
        self,
        path: str,
        *,
        tool: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self._call("POST", path, tool=tool, body=body, params=params)

    async def patch(
        self,
        path: str,
        *,
        tool: str,
        body: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self._call("PATCH", path, tool=tool, body=body, params=params)

    async def _call(
        self,
        method: str,
        path: str,
        *,
        tool: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        try:
            return await self.client.request(method, path, tool=tool, params=params, body=body)
        except AgentApiError as exc:
            raise ToolError(json.dumps(exc.to_payload(), ensure_ascii=False)) from exc
        except AgentApiTransportError as exc:
            raise ToolError(
                json.dumps(
                    {
                        "code": "TRANSPORT_ERROR",
                        "detail": "api_unreachable",
                        "hint": str(exc),
                    },
                    ensure_ascii=False,
                )
            ) from exc

    async def resolve_version(self, project_id: str) -> int:
        """Read the current project version so writes do not need it by hand."""
        detail = await self.get(f"{PROJECTS_PATH}/{project_id}", tool="get_project")
        project = detail.get("project") if isinstance(detail, dict) else None
        version = project.get("version") if isinstance(project, dict) else None
        if not isinstance(version, int):
            raise ToolError(
                json.dumps(
                    {
                        "code": "HTTP_ERROR",
                        "detail": "project_version_unavailable",
                        "hint": "读不到课题版本号，请先用 get_project 确认课题 id。",
                    },
                    ensure_ascii=False,
                )
            )
        return version

    async def apply_operations(
        self,
        project_id: str,
        *,
        tool: str,
        base_version: int | None,
        changed_fields: dict[str, Any] | None = None,
        operations: list[dict[str, Any]] | None = None,
        tz: str | None = None,
        dry_run: bool = False,
    ) -> Any:
        """Send one ``PATCH /agent/projects/{id}`` with fields and/or operations."""
        version = (
            base_version if base_version is not None else await self.resolve_version(project_id)
        )
        payload: dict[str, Any] = {
            "base_version": version,
            "changed_fields": changed_fields or {},
            "operations": operations or [],
        }
        params: dict[str, Any] = {}
        if tz:
            params["tz"] = tz
        if dry_run:
            params["dry_run"] = "true"
        return await self.patch(
            f"{PROJECTS_PATH}/{project_id}",
            tool=tool,
            body=payload,
            params=params or None,
        )


def _dry_run_params(dry_run: bool) -> dict[str, Any] | None:
    """The query parameters for a ``POST`` write tool."""
    return {"dry_run": "true"} if dry_run else None


def _context(ctx: Context) -> ToolContext:
    context = ctx.lifespan_context.get(CONTEXT_KEY)
    if not isinstance(context, ToolContext):
        raise ToolError(
            json.dumps(
                {
                    "code": "SERVER_NOT_READY",
                    "detail": "tool_context_missing",
                    "hint": "MCP 服务尚未初始化完成，请重试一次。",
                },
                ensure_ascii=False,
            )
        )
    return context


def _operation(
    action: str,
    project_id: str,
    changed_fields: dict[str, Any] | None = None,
    target_id: str | None = None,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "action": action,
        "project_id": project_id,
        "changed_fields": changed_fields or {},
    }
    if target_id:
        operation["target_id"] = target_id
    return operation


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _now_iso() -> str:
    """The current instant as an ISO 8601 string with a timezone."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _mutation_result(payload: Any) -> dict[str, Any]:
    """Normalize a mutation response into ``snapshot`` + ``action_receipts``."""
    if not isinstance(payload, dict):
        return {"result": payload}
    result: dict[str, Any] = {}
    for key in ("snapshot", "action_receipts"):
        if key in payload:
            result[key] = payload[key]
    for key, value in payload.items():
        if key not in result:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# read tools
# ---------------------------------------------------------------------------


async def get_today(ctx: Context, tz: str = "Asia/Shanghai") -> dict[str, Any]:
    """列出“今天”要做的事：已逾期、7 天内截止、今天该复查的等待项、最近进展。

    只读，不修改任何数据。按 tz 的日历日计算；tz 用 IANA 名称，例如 Asia/Shanghai、UTC。
    """
    return await _context(ctx).get(
        "/api/v1/agent/today", tool="get_today", params={"tz": tz}
    )


async def list_projects(ctx: Context, external_ref: str | None = None) -> dict[str, Any]:
    """列出这把 Key 有权限的课题（不含已归档）。

    只读。external_ref 用于按你在自己系统里的标记查一条课题，例如
    "litflow:nurse-scheduling-algorithm"。
    每条课题带 stage_entered_at（进入当前阶段的时间，ISO 8601，带时区，可能为 null）
    与 days_in_stage（在当前阶段停留的整天数，向下取整，不为负；未知时为 null）：
    这是两个事实，是否停留过久由你判断。
    """
    params = {"external_ref": external_ref} if external_ref else None
    return await _context(ctx).get(
        "/api/v1/agent/projects", tool="list_projects", params=params
    )


async def get_project(ctx: Context, project_id: str) -> dict[str, Any]:
    """读一个课题的现状：未完成节点、未完成等待项、投稿、审稿轮次、最近进展。

    只读。project_id 是课题 id；先用 list_projects 拿到。
    节点与等待项带 updated_at（ISO 8601，带时区）与 days_since_update（整天数）：
    这是两个事实，是否停滞由你判断。
    课题本身带 stage_entered_at（进入当前阶段的时间，ISO 8601，带时区，可能为 null）
    与 days_in_stage（在当前阶段停留的整天数，向下取整，不为负；未知时为 null）。
    """
    return await _context(ctx).get(f"{PROJECTS_PATH}/{project_id}", tool="get_project")


async def get_changes(
    ctx: Context, cursor: str | None = None, limit: int = 50
) -> dict[str, Any]:
    """只看变化：自游标以来有权限课题的变更摘要。

    只读。首次不带 cursor 调用返回当前游标且 changes 为空（从现在开始订阅）；
    之后把响应里的 next_cursor 原样传回即可继续。changed_fields 只有字段名，
    不含字段值；要看内容就用 get_project 重读该课题。limit 取 1–200，默认 50。
    """
    params: dict[str, Any] = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await _context(ctx).get(
        "/api/v1/agent/changes", tool="get_changes", params=params
    )


async def get_schema(ctx: Context) -> dict[str, Any]:
    """取这份接口的机器可读说明：课题类型与阶段、枚举、每个操作可写字段、字段长度上限。

    只读。第一次动手前先调用一次，不要凭记忆写枚举或长度。
    """
    context = _context(ctx)
    payload = await context.get("/api/v1/agent/schema", tool="get_schema")
    if isinstance(payload, dict):
        context.set_schema(AgentSchema.from_payload(payload))
    return payload


# ---------------------------------------------------------------------------
# write tools
# ---------------------------------------------------------------------------


async def create_project(
    ctx: Context,
    title: str,
    template_id: str,
    objective: str = "",
    stage: str | None = None,
    status_note: str | None = None,
    external_ref: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """新建一个课题。

    会写入服务端。带 external_ref 时可重复调用：同一 external_ref 不会重复建，
    已存在就返回那条课题。stage 省略时取该课题类型的第一个阶段。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    body = _drop_empty(
        {
            "title": title,
            "template_id": template_id,
            "objective": objective,
            "stage": stage,
            "status_note": status_note,
            "external_ref": external_ref,
        }
    )
    payload = await _context(ctx).post(
        PROJECTS_PATH,
        tool="create_project",
        body=body,
        params=_dry_run_params(dry_run),
    )
    return _mutation_result(payload)


async def update_project(
    ctx: Context,
    project_id: str,
    base_version: int | None = None,
    title: str | None = None,
    objective: str | None = None,
    stage: str | None = None,
    status_note: str | None = None,
    owner_label: str | None = None,
    tz: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """改一个课题的现状字段：标题、目标、阶段、现状说明、负责人标签。

    会写入服务端。只改你显式传入的字段；其余保持不变。
    base_version 省略时会自动读当前版本。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    changed_fields = _drop_empty(
        {
            "title": title,
            "objective": objective,
            "stage": stage,
            "status_note": status_note,
            "owner_label": owner_label,
        }
    )
    payload = await _context(ctx).apply_operations(
        project_id,
        tool="update_project",
        base_version=base_version,
        changed_fields=changed_fields,
        tz=tz,
        dry_run=dry_run,
    )
    return _mutation_result(payload)


async def upsert_node(
    ctx: Context,
    project_id: str,
    kind: str,
    title: str,
    detail: str | None = None,
    due_at: str | None = None,
    assignee_label: str | None = None,
    target_id: str | None = None,
    base_version: int | None = None,
    tz: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """加一个节点（截止 / 任务 / 里程碑 / 进展），或改已有的节点。

    会写入服务端。target_id 为空则新建，有值则改那个节点。
    kind 为 deadline 时必须给 due_at。只写日期（YYYY-MM-DD）按 tz 解释为当天结束。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    changed_fields = _drop_empty(
        {
            "kind": kind,
            "title": title,
            "detail": detail,
            "due_at": due_at,
            "assignee_label": assignee_label,
        }
    )
    payload = await _context(ctx).apply_operations(
        project_id,
        tool="upsert_node",
        base_version=base_version,
        operations=[_operation("upsert_node", project_id, changed_fields, target_id)],
        tz=tz,
        dry_run=dry_run,
    )
    return _mutation_result(payload)


async def complete_node(
    ctx: Context,
    project_id: str,
    node_id: str,
    completed_at: str | None = None,
    base_version: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """把一个节点标记为已完成。

    会写入服务端。node_id 是节点 id，先用 get_project 取。
    completed_at 省略时用当前时间；只写日期按当前时区解释。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    changed_fields: dict[str, Any] = {"completed_at": completed_at or _now_iso()}
    payload = await _context(ctx).apply_operations(
        project_id,
        tool="complete_node",
        base_version=base_version,
        operations=[_operation("upsert_node", project_id, changed_fields, node_id)],
        dry_run=dry_run,
    )
    return _mutation_result(payload)


async def upsert_waiting_item(
    ctx: Context,
    project_id: str,
    title: str,
    status: str = "open",
    blocked_by_label: str | None = None,
    next_check_at: str | None = None,
    target_id: str | None = None,
    base_version: int | None = None,
    tz: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """加一个“等别人”的待处理项，或改已有的待处理项。

    会写入服务端。next_check_at 决定它什么时候出现在 get_today 里；
    不写 next_check_at 的待处理项永远不会被列出来。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    changed_fields = _drop_empty(
        {
            "title": title,
            "status": status,
            "blocked_by_label": blocked_by_label,
            "next_check_at": next_check_at,
        }
    )
    payload = await _context(ctx).apply_operations(
        project_id,
        tool="upsert_waiting_item",
        base_version=base_version,
        operations=[_operation("upsert_waiting_item", project_id, changed_fields, target_id)],
        tz=tz,
        dry_run=dry_run,
    )
    return _mutation_result(payload)


async def complete_waiting_item(
    ctx: Context,
    project_id: str,
    waiting_item_id: str,
    base_version: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """把一个待处理项标记为已完成（等到了）。

    会写入服务端。waiting_item_id 先用 get_project 取。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    payload = await _context(ctx).apply_operations(
        project_id,
        tool="complete_waiting_item",
        base_version=base_version,
        operations=[_operation("complete_waiting_item", project_id, {}, waiting_item_id)],
        dry_run=dry_run,
    )
    return _mutation_result(payload)


async def upsert_submission(
    ctx: Context,
    project_id: str,
    journal_name: str,
    status: str = "draft",
    journal_issn: str | None = None,
    submitted_at: str | None = None,
    decided_at: str | None = None,
    apc_notes: str | None = None,
    target_id: str | None = None,
    base_version: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """记录一次投稿，或改已有的投稿记录。

    会写入服务端。改 status 会自动在动态里记一条投稿状态变化。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    changed_fields = _drop_empty(
        {
            "journal_name": journal_name,
            "status": status,
            "journal_issn": journal_issn,
            "submitted_at": submitted_at,
            "decided_at": decided_at,
            "apc_notes": apc_notes,
        }
    )
    payload = await _context(ctx).apply_operations(
        project_id,
        tool="upsert_submission",
        base_version=base_version,
        operations=[_operation("upsert_submission", project_id, changed_fields, target_id)],
        dry_run=dry_run,
    )
    return _mutation_result(payload)


async def add_review_round(
    ctx: Context,
    project_id: str,
    round_number: int = 1,
    status: str = "open",
    comments_markdown: str = "",
    response_markdown: str = "",
    due_at: str | None = None,
    target_id: str | None = None,
    base_version: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """记一轮审稿意见与回复，或改已有的一轮。

    会写入服务端。round_number 是第几轮；comments_markdown 放审稿意见，
    response_markdown 放你的回复。status 常用 open / resolved。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    changed_fields = _drop_empty(
        {
            "round_number": round_number,
            "status": status,
            "comments_markdown": comments_markdown,
            "response_markdown": response_markdown,
            "due_at": due_at,
        }
    )
    payload = await _context(ctx).apply_operations(
        project_id,
        tool="add_review_round",
        base_version=base_version,
        operations=[_operation("upsert_review_round", project_id, changed_fields, target_id)],
        dry_run=dry_run,
    )
    return _mutation_result(payload)


async def append_timeline(
    ctx: Context,
    project_id: str,
    title: str,
    detail: str | None = None,
    kind: str = "update",
    occurred_at: str | None = None,
    due_at: str | None = None,
    base_version: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """往课题动态里追加一条进展记录。

    会写入服务端。kind 通常是 update（进展）；它会出现在 get_today 的最近进展里。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    changed_fields = _drop_empty(
        {
            "kind": kind,
            "title": title,
            "detail": detail,
            "occurred_at": occurred_at,
            "due_at": due_at,
        }
    )
    payload = await _context(ctx).apply_operations(
        project_id,
        tool="append_timeline",
        base_version=base_version,
        operations=[_operation("append_timeline_event", project_id, changed_fields)],
        dry_run=dry_run,
    )
    return _mutation_result(payload)


async def archive_project(
    ctx: Context, project_id: str, dry_run: bool = False
) -> dict[str, Any]:
    """归档一个课题。

    破坏性操作：它会改变课题状态，归档后课题不再出现在列表里。
    归档后用同一 external_ref 会建出新课题。
    dry_run=true 时只预演：返回同样的回执，不落库；确认无误再正式执行。
    """
    payload = await _context(ctx).post(
        f"{PROJECTS_PATH}/{project_id}/archive",
        tool="archive_project",
        params=_dry_run_params(dry_run),
    )
    return _mutation_result(payload)




reference_http_factory = references.UrlLibHttpClient


async def verify_references(bibtex: str) -> dict[str, Any]:
    """只读：核验 BibTeX 参考文献与公开数据库的元数据一致性，不判断文献真伪或质量。

    需要联网；本机将 DOI、题名等题录元数据发送至 Crossref 和 NCBI PubMed，
    不发送给极科研服务端。只传参考文献题录，不要传稿件正文或任何患者信息。
    每次最多 50 条。必须先设置你自己的联系邮箱 JIKEYAN_CONTACT_EMAIL
    （只随请求发给 Crossref / NCBI，不发给极科研服务端）；NCBI_API_KEY 可选。
    unresolved 常见于会议摘要、标准、信件等无 DOI 条目或数据库不可用。
    标识符不存在为 mismatch，查询失败为 unresolved 并注明失败，二者不同。
    任一轨 mismatch 则总体 mismatch；否则任一轨 verified 则总体 verified，
    另一轨未解析或查询失败时注明；两轨 unresolved 则总体 unresolved。
    """
    try:
        email = references.require_contact_email(os.environ.get("JIKEYAN_CONTACT_EMAIL", ""))
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    key = os.environ.get("NCBI_API_KEY", "")
    client = reference_http_factory(contact_email=email, ncbi_api_key=key)
    try:
        return await asyncio.to_thread(references.verify_references, bibtex, contact_email=email, ncbi_api_key=key, http=client)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


async def check_topic_collision(title: str, keywords: list[str] | None = None, study_type: str = "other", concept_groups: list[list[str]] | None = None) -> dict[str, Any]:
    """只读：在选题阶段检索 ClinicalTrials.gov 与 PubMed 已发表综述。

    由你（Agent）把选题拆成 2–4 个核心概念，每个概念给出首选表述和同义词（英文为主，必要时加中文），按重要性排序后传入 concept_groups；不传则用启发式，质量有限。
    例如 [["citrate anticoagulation", "regional citrate anticoagulation"], ["continuous renal replacement therapy", "CRRT"], ["accumulation", "citrate accumulation"]]。
    PROSPERO 未检索；零命中不等于没人做过，本工具不给选题结论。需要联网；
    必须配置自己的 JIKEYAN_CONTACT_EMAIL，邮箱只发给 NCBI 等公开接口，
    CTG 请求的 User-Agent 也含邮箱，不发给极科研服务端。
    候选题名与关键词会发送到 ClinicalTrials.gov 与 PubMed 公开接口，
    不发送给极科研服务端；不要传患者信息，未发表的敏感细节请斟酌。
    """
    from jikeyan_mcp.local_search import topic_collision
    try:
        email = references.require_contact_email(os.environ.get("JIKEYAN_CONTACT_EMAIL", ""))
        key = os.environ.get("NCBI_API_KEY", "")
        client = reference_http_factory(contact_email=email, ncbi_api_key=key)
        return await asyncio.to_thread(topic_collision.check_topic_collision, title, keywords, study_type, concept_groups=concept_groups, contact_email=email, ncbi_api_key=key, http=client)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


#: The read-only tools.
READ_TOOLS = (get_today, list_projects, get_project, get_changes, get_schema, verify_references, check_topic_collision)

#: Every tool, in listing order.
ALL_TOOLS = (
    get_today,
    list_projects,
    get_project,
    get_changes,
    get_schema,
    verify_references,
    check_topic_collision,
    create_project,
    update_project,
    upsert_node,
    complete_node,
    upsert_waiting_item,
    complete_waiting_item,
    upsert_submission,
    add_review_round,
    append_timeline,
    archive_project,
)

READ_TOOL_NAMES = frozenset(tool.__name__ for tool in READ_TOOLS)

#: Tools that cannot be undone by re-running them.
DESTRUCTIVE_TOOL_NAMES = frozenset({"archive_project"})


def tool_annotations(tool_name: str) -> dict[str, Any]:
    """Return the MCP tool annotations for one tool."""
    if tool_name in READ_TOOL_NAMES:
        return {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    return {
        "readOnlyHint": False,
        "destructiveHint": tool_name in DESTRUCTIVE_TOOL_NAMES,
        "idempotentHint": False,
        "openWorldHint": True,
    }


def privacy_suffix() -> str:
    """The compliance sentence appended to every tool description."""
    return PRIVACY_NOTICE

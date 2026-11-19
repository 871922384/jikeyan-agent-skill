# Agent API 端点表

Base: `https://api.jikeyan.cn`（下表路径均接在其后）。
来源：`app/api/v1/external_agent.py`（jikeyan-api main 分支）与线上权威指南
`https://api.jikeyan.cn/agent.md`。每条路径均已核对存在，未虚构。
只列出已上线的端点；会话类端点需要用户登录态，不属于 agent key 范围。

## Agent Key 可用（本 skill 范围，`Authorization: Bearer <agent key>`）

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/v1/agent/schema` | 机器可读接口说明：templates/阶段表、node_kinds、submission_statuses、waiting_item_statuses、operations 允许字段、limits、guide 全文 |
| GET | `/api/v1/agent/today` | 今天的工作：overdue、due_soon（7 天）、waiting_to_check、recent_updates（48h）；可选 `?tz=<IANA>`，默认 `Asia/Shanghai` |
| GET | `/api/v1/agent/changes` | 增量变更摘要（`cursor`、`limit` 1–200；changed_fields 只有字段名，不含值） |
| GET | `/api/v1/agent/projects` | 列出有权限的未归档项目；可选 `?external_ref=<ref>` 按引用查询 |
| POST | `/api/v1/agent/projects` | 新建项目（`title`、`template_id` 必填；可选 `objective`、`stage`、`status_note`、`external_ref`）。同账号同 `external_ref` 未归档已存在时返回 200 + 已存在快照，不重复创建；支持 `?dry_run=true` |
| GET | `/api/v1/agent/projects/{project_id}` | 读项目：`project`（含 `version`）、`open_nodes`、`open_waiting_items`、`submissions`、`review_rounds`、`recent_updates` |
| PATCH | `/api/v1/agent/projects/{project_id}` | 改字段 + `operations`；需 `base_version`；可选 `?tz=<IANA>`、`Idempotency-Key` 请求头、`?dry_run=true` |
| POST | `/api/v1/agent/projects/{project_id}/archive` | 归档项目（不可撤销）；支持 `?dry_run=true` |

## 用户登录态（`get_current_account`，非 agent key；本 skill 默认不用）

| Method | Path | 用途 |
|---|---|---|
| GET / POST | `/api/v1/agent/conversations` | 会话列表 / 新建会话 |
| GET | `/api/v1/agent/conversations/{conversation_id}/messages` | 读会话消息 |
| POST | `/api/v1/agent/conversations/{conversation_id}/messages` | 发消息（202 + run；异步执行） |
| GET | `/api/v1/agent/runs/{run_id}` | 查 run 状态 |
| POST | `/api/v1/agent/runs/{run_id}/cancel` | 取消 run |

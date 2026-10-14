---
name: jikeyan-agent
description: Use when reading or writing 极科研 (jikeyan) research projects via the Agent API. Triggers: 极科研, jikeyan, 课题, 节点, 等待项, 投稿.
---

# 极科研 (jikeyan) Agent API

Read and write research projects (课题) through the Agent API.
Base URL: `https://api.jikeyan.cn` (override with `JIKEYAN_API_BASE`).
Helper: `scripts/jikeyan.sh`. Full table: `references/endpoints.md`.

## 0. Auth & 合规 (read first)

- Key from env only: `Authorization: Bearer $JIKEYAN_API_KEY`. Never hard-code,
  log, or paste the key anywhere.
- **Never send patient names, hospital IDs, diagnoses, or follow-up text.**
  The API has no fields for them; unknown fields are rejected — keep it that way.

## 1. Schema first

Before writing enums or operations, fetch the machine-readable schema
(same source as the server code — stages, kinds, operations, limits):

```bash
scripts/jikeyan.sh get /api/v1/agent/schema
```

It returns `templates` (per-`template_id` stage list, plus `paused`),
`node_kinds`, `submission_statuses`, `waiting_item_statuses`,
`operations` (allowed fields per action), `limits`, and `guide_markdown`.
Trust it over memory.

## 2. Reads

```bash
scripts/jikeyan.sh get "/api/v1/agent/projects"                          # list (unarchived)
scripts/jikeyan.sh get "/api/v1/agent/projects?external_ref=<ref>"       # lookup by ref
scripts/jikeyan.sh get "/api/v1/agent/projects/<project_id>"             # detail
scripts/jikeyan.sh get "/api/v1/agent/today?tz=Asia%2FShanghai"           # today's work
```

- Detail returns `project` (note `project.version`), `open_nodes`,
  `open_waiting_items`, `submissions`, `review_rounds`, `recent_updates` (latest 20).
- `today` returns `overdue`, `due_soon` (7d), `waiting_to_check`, `recent_updates`
  (48h, excludes your own `source=user` notes). `tz` is an IANA zone, default `Asia/Shanghai`.
- Waiting items without `next_check_at` never appear in `today` — always set it.

## 3. Create (idempotent via external_ref)

```bash
scripts/jikeyan.sh post /api/v1/agent/projects \
  '{"title":"护考排班算法","objective":"……","template_id":"paper","external_ref":"litflow:nurse-scheduling-algorithm"}'
```

- `external_ref` (≤200 chars, e.g. `<your-system>:<id>`) marks the project's
  identity on your side. Same ref + unarchived project → `200` with existing
  snapshot (`action_receipts[0].summary` = "已存在，未重复创建"), no duplicate.
- Archived projects are excluded from dedup (reusing a ref after archiving creates new).
- Batch import: `POST` with `external_ref`, then one `PATCH` carrying all `operations`.

## 4. Patch (read → write with version)

1. `GET` the project, note `project.version`.
2. `PATCH` with equal `base_version`. `changed_fields` may set `title`,
   `objective`, `status_note` (≤120), `stage`, `owner_label`;
   `stage` must be in the project's template stage table (else 422).
   Every operation's `project_id` must equal the URL project.

```bash
scripts/jikeyan.sh patch /api/v1/agent/projects/<id> \
  '{"base_version":2,"changed_fields":{"status_note":"已提交修回，等外审","stage":"revision"},"operations":[]}'
```

Optional `?tz=<IANA>` query and `Idempotency-Key` header (same key replays the
stored response instead of writing twice):

```bash
JIKEYAN_IDEMPOTENCY_KEY=status-note-1 scripts/jikeyan.sh \
  patch "/api/v1/agent/projects/<id>?tz=Asia%2FShanghai" '{...}'
```

Operations (`action`, `project_id`, `target_id` empty = create):

| action | notes |
|---|---|
| `upsert_node` | fields: `kind` (`deadline` needs `due_at`, `task`, `milestone`, `update`), `title`, `detail`, `due_at`, `completed_at` (set = done), `assignee_label` |
| `upsert_waiting_item` | fields: `title`, `status`, `blocked_by_label`, `next_check_at` (always set it) |
| `upsert_submission` | fields: `journal_name`, `journal_issn`, `status`, `submitted_at`, `decided_at`, `apc_notes` |
| `upsert_review_round` | fields: `round_number`, `status`, `comments_markdown`, `response_markdown`, `due_at` |
| `append_timeline_event` | progress note (no `kind` needed; defaults to `kind=update`) |
| `complete_waiting_item` | `target_id` required, `changed_fields` must be empty |

## 5. Archive

```bash
scripts/jikeyan.sh post /api/v1/agent/projects/<id>/archive
```

## 6. Errors

Failure shape keeps `code`/`detail` plus actionable `details`:

```json
{"code":"HTTP_ERROR","detail":"invalid_stage","details":{"field":"stage","allowed":[...]}}
```

| detail | fix |
|---|---|
| `version_conflict` (409) | read `details.current_version`, re-`GET`, resubmit with fresh `base_version` |
| `invalid_operation_fields` | check `details.action` / `unknown_fields` vs `allowed_fields`; re-fetch schema |
| `invalid_stage` / `invalid_template_id` / `invalid_node_kind` / `invalid_submission_status` | use `details.allowed` values |
| `target_required` / `target_not_found_or_forbidden` | pass a valid `target_id` of the same project |
| `operation_project_mismatch` | operation `project_id` ≠ URL project |
| `invalid_datetime` / `invalid_timezone` | ISO-8601 datetime or valid IANA zone |

## 7. Dates

- `due_at` / `next_check_at` accept `YYYY-MM-DD` or full ISO-8601.
- Date-only: `due_at` = that day 23:59:59, `next_check_at` = 09:00, interpreted
  in the request `tz` (default `Asia/Shanghai`). So `2026-10-15` means
  "by end of that day", never midnight-start.
- Full datetimes (e.g. `2026-10-15T16:00:00+08:00`) keep their own zone.

## 8. Field limits

`title` ≤300, `status_note` ≤120, `external_ref` ≤200, node `detail` ≤4000,
`assignee_label` ≤200. Confirm via `limits` in `GET /agent/schema`.

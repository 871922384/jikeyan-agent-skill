# jikeyan-mcp — 极科研官方 MCP 服务

<!-- mcp-name: io.github.871922384/jikeyan-agent-skill -->

给外部 Agent 客户端（Claude Code、Codex、Cursor 等）用的官方 MCP 服务，
形态是**用户本机运行的 stdio 进程**。让你的 agent 直接读写
[极科研](https://jikeyan.cn)（iOS 科研项目看板 App）中的项目、节点、
等待项、投稿与审稿记录。

除 `verify_references` 与 `check_topic_collision` 外，工具只调用现有的
`/api/v1/agent/*` HTTP 接口：

`verify_references` 在本机直接把题录中的 DOI、题名及查询所需元数据发往 Crossref 和 NCBI PubMed 公开接口，不发往极科研服务端。只传参考文献题录，不传正文或患者信息。数据来源为 Crossref / NCBI PubMed，不暗示其背书。结论只表示元数据一致性，不判断真伪或质量；任一轨 `mismatch`（包括给定 DOI 或 PMID 在对应数据库中不存在）时总体为 `mismatch`；否则一轨 `verified` 时总体为 `verified`，另一轨未解析或查询失败会注明；两轨均 `unresolved` 时总体为 `unresolved`。查询失败不同于查不到记录，失败轨标记 `lookup_failed` 并提示重试。

`check_topic_collision` 在本机把候选题名和关键词发送到 ClinicalTrials.gov 与 NCBI PubMed，不发给极科研服务端。不要传患者信息，未发表的敏感细节请斟酌。必须配置自己的 `JIKEYAN_CONTACT_EMAIL`，NCBI 收到邮箱，ClinicalTrials.gov 的 User-Agent 也包含邮箱。PROSPERO 未检索；零命中不等于没有人做过，不提供可行性结论。结果包含各检索式、来源总数、取回数和 UTC 日期；数据来自 ClinicalTrials.gov（美国国家医学图书馆）及 NCBI PubMed，经本工具截取与摘要，具体检索日期随输出列明。

- **不绕过鉴权**：每个请求都带 `Authorization: Bearer <Agent Key>`，权限完全由服务端判定。
- **不直连数据库**：MCP 进程里没有数据库访问，只通过公开 HTTP 接口读写。
- **不落盘**：不写任何请求或响应内容；日志里只有工具名与 HTTP 状态码，没有 Key、没有内容。
- **不放宽规则**：服务端不接收患者姓名、住院号、诊断或随访文本，MCP 层同样不接收。

## 安装

需要 Python 3.10+。最简单的方式（包发布到 PyPI 后）：

```bash
uvx jikeyan-mcp
```

PyPI 发布前，也可以用 git 直接运行：

```bash
uvx --from "jikeyan-mcp @ git+https://github.com/871922384/jikeyan-agent-skill#subdirectory=mcp" jikeyan-mcp
```

或本地安装：

```bash
pip install jikeyan-mcp        # PyPI 发布后
pipx install jikeyan-mcp       # 隔离安装，同样提供 jikeyan-mcp 命令
cd mcp && pip install -e '.[test]'   # 本仓库开发：可编辑安装 + 测试依赖
```

## 配置

环境变量：

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `JIKEYAN_AGENT_KEY` | 是 | 无 | App 内生成的 Agent Key。缺失时进程直接退出并给出明确提示，**不会打印 Key** |
| `JIKEYAN_API_BASE_URL` | 否 | `https://api.jikeyan.cn` | API 根地址（须以 `http://` 或 `https://` 开头） |
| `JIKEYAN_CONTACT_EMAIL` | 两个本机检索工具必填 | 无 | 你自己的联系邮箱。Crossref 与 NCBI 要求公开接口的调用方留下联系方式；它随请求发给相关公开来源（ClinicalTrials.gov 使用 User-Agent），不发送给极科研服务端，也不落盘。未配置时相关工具直接报错，不会发出任何请求 |
| `NCBI_API_KEY` | 否 | 无 | PubMed API key（可选，提高配额） |

```bash
export JIKEYAN_AGENT_KEY="jk_..."
export JIKEYAN_API_BASE_URL="https://api.jikeyan.cn"   # 可省略
jikeyan-mcp
```

Key 在 App 内生成：App 中 **设置 → 连接智能体** 生成 Agent Key，
把它粘贴到环境变量或所用客户端的 secret 配置里。不要把 Key 写进仓库、
聊天记录或日志。

## Claude Code 配置

`.mcp.json`（项目级）：

```json
{
  "mcpServers": {
    "jikeyan": {
      "command": "uvx",
      "args": ["jikeyan-mcp"],
      "env": {
        "JIKEYAN_AGENT_KEY": "${JIKEYAN_AGENT_KEY}",
        "JIKEYAN_API_BASE_URL": "https://api.jikeyan.cn"
      }
    }
  }
}
```

也可以用 CLI（Key 只留在本机配置里，不要提交仓库）：

```bash
claude mcp add jikeyan \
  -e JIKEYAN_AGENT_KEY="$JIKEYAN_AGENT_KEY" \
  -e JIKEYAN_API_BASE_URL=https://api.jikeyan.cn \
  -- uvx jikeyan-mcp
```

## Codex 配置

```bash
codex mcp add jikeyan \
  --env JIKEYAN_AGENT_KEY="$JIKEYAN_AGENT_KEY" \
  --env JIKEYAN_API_BASE_URL=https://api.jikeyan.cn \
  -- uvx jikeyan-mcp
```

`codex mcp list` 可以确认注册成功。

## 其他 MCP 客户端

任何支持 stdio MCP 服务的客户端均可使用，启动命令为 `uvx jikeyan-mcp`
（PyPI 发布前用上面的 git 方式），环境变量按上表配置。
Cursor、Windsurf、Gemini CLI 等按各自文档添加 stdio 服务即可。

## 工具

一共 17 个，按意图命名，不镜像 REST 路径。写操作带 `readOnlyHint` / `destructiveHint` / `idempotentHint` 标注。

| 工具 | 读/写 | 说明 |
| --- | --- | --- |
| `check_topic_collision` | 读 | 本机联网检索 ClinicalTrials.gov 与 PubMed 综述，PROSPERO 未检索 |
| `verify_references` | 读 | 本机联网核对 BibTeX 元数据，每次最多 50 条 |
| `get_schema` | 读 | 机器可读的接口说明：项目类型与阶段、枚举、可写字段、长度上限 |
| `get_today` | 读 | 已逾期、7 天内截止、今天该复查的等待项、最近进展 |
| `list_projects` | 读 | 有权限的项目；可按 `external_ref` 过滤；每项带 `stage_entered_at` / `days_in_stage` |
| `get_project` | 读 | 项目现状：未完成节点、未完成等待项、投稿、审稿轮次、最近进展；节点与等待项带 `updated_at` / `days_since_update` |
| `get_changes` | 读 | 自游标以来的变更摘要（`entity_type`、`entity_id`、`changed_fields` 字段名、`by_you`）；首次调用只返回游标 |
| `create_project` | 写 | 新建项目；带 `external_ref` 时可重复调用而不重复建 |
| `update_project` | 写 | 改标题、目标、阶段、现状说明、负责人标签 |
| `upsert_node` | 写 | 新建或修改节点（截止 / 任务 / 里程碑 / 进展） |
| `complete_node` | 写 | 把节点标记为已完成 |
| `upsert_waiting_item` | 写 | 新建或修改「等别人」的待处理项 |
| `complete_waiting_item` | 写 | 把待处理项标记为已完成 |
| `upsert_submission` | 写 | 记录或修改投稿 |
| `add_review_round` | 写 | 记录一轮审稿意见与回复 |
| `append_timeline` | 写 | 追加一条进展记录 |
| `archive_project` | 写（**破坏性**） | 归档项目；归档后不再出现在列表里 |

字段上限与枚举不在本包里写死：它们在服务启动时从 `GET /agent/schema` 拉取，写进工具描述和参数
JSON Schema。因此不会出现「文档写 300、代码写 500」这种漂移。

### 先预演再执行（`dry_run`）

除 `get_*` / `verify_references` / `check_topic_collision` 外，写工具都多一个可选参数 `dry_run`（默认 `false`），映射为服务端查询参数 `?dry_run=true`。

- 预演返回**同格式**回执（`snapshot` / `action_receipts`），并带 `"dry_run": true`；
  服务端不落库，响应里的 `snapshot.version` 是「如果执行会得到的版本」。
- 校验错误、版本冲突、Key 权限（只读 / 范围外项目 / 范围 Key 建项目）在预演时返回同样的错误。
- 预演不占用幂等记录；正式执行时响应里的 `dry_run` 为 `false`。

### 错误处理

服务端错误体里的 `code`、`detail`、`hint` 原样透传给 Agent，`details` 也一并带上。
`hint` 是给 Agent 自己纠正用的固定文案，不含用户输入。按 `hint` 改一次再重试即可。

## 已知限制

- **跨项目搜索、共享笔记、评论、通知、期刊查询等能力**目前没有 MCP 工具；变更游标由 `get_changes` 提供，写前预演由 `dry_run` 提供。
- **Key 权限由服务端判定**：MCP 不额外拦截。只读 Key 或范围外项目会收到 403
 （`key_read_only` / `project_not_writable_for_key` / `key_scope_forbids_create`）
  和固定 `hint`，按提示到 App 里重新生成 Key。
- **不开放团队类动作**：节点指派、成员管理、加入申请会影响他人，不开放。
- **附件不开放**：MCP 层不传文件内容。
- **`base_version` 乐观锁**：写操作走服务端的版本检查。工具默认先读一次当前版本再写，所以一般不会撞上
  `version_conflict`；但如果撞上，错误里带 `details.current_version`，重新读一次再写。
- **归档不可撤销**：本版没有「取消归档」接口，归档后只能用同一 `external_ref` 建新项目。
- **不传 `Idempotency-Key`**：MCP 工具调用没有幂等键的入口。重复写同一节点是「再 upsert 一次」，
  不会像 HTTP 接口那样原样重放。建项目靠 `external_ref` 幂等。
- **本机进程**：服务在你自己的机器上跑，Key 也在本机环境变量里。不要把 Key 写进仓库里的
  `.mcp.json` 后再提交；用 `claude mcp add -e` 或本地不入库的 `.mcp.json`。
- **`fastmcp` 会联网检查新版本**：只有启动横幅路径会检查，stdio 模式已关闭横幅
  （`show_banner=False`），不会因此发起网络请求。

## 测试

```bash
cd mcp && python -m pytest -q
```

测试用 `httpx.MockTransport` 伪造服务端响应，不联网、不碰生产库。

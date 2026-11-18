# jikeyan-agent-skill（中文）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP: stdio](https://img.shields.io/badge/MCP-stdio-blue)](mcp/README.md)

**[极科研 (jikeyan)](https://jikeyan.cn) 官方 Agent 技能 + MCP 服务——让你的 AI 智能体帮你管理科研项目、节点、等待项、投稿与审稿。**

极科研是一款本地优先的 iOS 科研项目看板 App。本仓库是它的官方智能体入口：
两个可安装的 skill + 一个独立 MCP 服务，都调用同一份公开 Agent API
（[在线指南](https://api.jikeyan.cn/agent.md)）。

> English version: [README.md](README.md).

## 你的 agent 能帮你做什么

以下每一条都对应真实存在的 skill 工作流或 MCP 工具：

1. **每日简报**——已逾期节点、7 天内截止、今天该复查的等待项、最近 48 小时进展（`get_today` + 每日复盘工作流）。
2. **追等待项**——找出停滞的“等别人”事项，起草中英文跟进话术（只起草、不代发，发送永远由你完成）。
3. **批量导入项目**——用你自己的 `external_ref` 幂等建项目，一次 patch 写完所有节点。
4. **审稿回复拆解**——把审稿意见拆成编号事项，起草逐条回复信，记录审稿轮次（`add_review_round`）。
5. **投稿前检查**——期刊要求、伦理、作者、参考文献、图表、cover letter，逐项核对。
6. **截止日倒排**——从硬性截止倒推，预留外部反馈与合作者确认的缓冲。
7. **文献核验与选题撞题**——用 Crossref / PubMed 核对 BibTeX 元数据，用 ClinicalTrials.gov + PubMed 综述做选题检索（本机运行，不经过极科研服务端）。
8. **每周复盘**——本周完成、下周截止、停滞项、需要你拍板的事项。

## 三步上手

**1. 生成 key**——在极科研 App：**设置 → 连接智能体**，生成 Agent Key。

**2. 设环境变量**——key 只放在环境变量里，绝不进仓库：

```bash
export JIKEYAN_AGENT_KEY='<你的 agent key>'
```

**3. 安装 skill 或 MCP 服务**——选一行：

| 客户端 | Skill | MCP 服务 |
|---|---|---|
| Claude Code | `/plugin marketplace add 871922384/jikeyan-agent-skill` 后 `/plugin install jikeyan@jikeyan`（或把 `plugins/jikeyan/skills/*` 拷到 `~/.claude/skills/`） | 下方 `.mcp.json` 片段 |
| Codex | 把 `plugins/jikeyan/skills/*` 拷到 `~/.codex/skills/` | 下方 `codex mcp add …` 片段 |
| Cursor / Windsurf / 其他 MCP 客户端 | 把 `plugins/jikeyan/skills/*` 拷到对应 skills 目录 | 通用 stdio 配置见下方 |

装好后跟 agent 说“用 jikeyan skill，先调 `get_schema`”。

### MCP 配置片段

Claude Code `.mcp.json`（项目级；若含 key 请不要提交）：

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

Codex：

```bash
codex mcp add jikeyan \
  --env JIKEYAN_AGENT_KEY="$JIKEYAN_AGENT_KEY" \
  --env JIKEYAN_API_BASE_URL=https://api.jikeyan.cn \
  -- uvx jikeyan-mcp
```

其他客户端（Cursor、Windsurf、Gemini CLI……）：添加 stdio 服务，
命令 `uvx`、参数 `["jikeyan-mcp"]`，环境变量按上表配置。
`uvx jikeyan-mcp` 需要 `jikeyan-mcp` 已发布到 PyPI；发布前可用：

```bash
uvx --from "jikeyan-mcp @ git+https://github.com/871922384/jikeyan-agent-skill#subdirectory=mcp" jikeyan-mcp
```

不用 MCP 也行：`plugins/jikeyan/skills/jikeyan-agent/scripts/jikeyan.sh`
是同 API 的 curl 封装——`JIKEYAN_AGENT_KEY` + `get/post/patch`。

## 目录

| 路径 | 内容 |
|---|---|
| `plugins/jikeyan/skills/jikeyan-agent/` | Skill：Agent API 操作手册 + `jikeyan.sh` + 端点表 |
| `plugins/jikeyan/skills/jikeyan-academic-colleague/` | Skill：科研管理工作流（每日/每周复盘、停滞判断、等待项跟进、审稿回复、投稿前检查、倒排计划） |
| `mcp/` | 独立 Python 包 `jikeyan-mcp`（17 个 MCP 工具，stdio），见 [mcp/README.md](mcp/README.md) |
| `.claude-plugin/marketplace.json` | Claude Code 插件市场清单 |
| `server.json` | 官方 MCP Registry 清单（已准备好，尚未提交） |
| `smithery.yaml` | Smithery 部署配置（已准备好，尚未提交） |
| `llms.txt` | 给 LLM 检索的仓库摘要 |
| `docs/distribution.md` | 格式出处、仓库元信息建议、需手动提交的平台清单 |

## 安全与隐私

- Agent Key 只从环境变量（`JIKEYAN_AGENT_KEY`）读取。不要写死、不要提交、不要贴到聊天记录或日志里。
- **不要向 API 发送患者姓名、住院号、诊断或随访原文**——接口本来就没有这些字段，未知字段会被拒绝。个人笔记只保存在设备端，不参与同步。
- MCP 服务跑在你自己的机器上；日志里只有工具名和 HTTP 状态码，没有 Key、没有内容。
- Key 权限（只读、限定项目范围）由服务端强制执行。Key 被撤销会返回 `401`，去 App 里重新生成即可。

## 链接

- 极科研：[https://jikeyan.cn](https://jikeyan.cn) · [App Store](https://apps.apple.com/app/id6785017540) · [隐私政策](https://jikeyan.cn/privacy)
- Agent API 在线指南：[https://api.jikeyan.cn/agent.md](https://api.jikeyan.cn/agent.md)
- MCP 包说明：[mcp/README.md](mcp/README.md)

## 协议

MIT，见 [LICENSE](LICENSE)。

# 极科研学术管理同事

这个知识包供个人 Agent 在本地加载，提供科研项目管理的工作方法和待确认的判断草案。数据事实来自极科研官方 MCP，推理在用户自己的 Agent 中进行；不提供诊疗建议。

## 安装技能

从本仓库根目录，将整个 `agent_skills/jikeyan-academic-colleague` 目录复制到所用客户端的技能目录，保留 `SKILL.md` 与 `references/` 的相对结构：

- Claude Code：个人使用放在 `~/.claude/skills/jikeyan-academic-colleague/`，项目使用放在项目的 `.claude/skills/jikeyan-academic-colleague/`。
- Codex：个人使用放在 `~/.codex/skills/jikeyan-academic-colleague/`，项目使用放在项目的 `.agents/skills/jikeyan-academic-colleague/`。

按客户端的技能发现机制重新加载或开启新会话；可在请求中明确说使用 `jikeyan-academic-colleague`。

## 配合 MCP

按仓库 [MCP 安装配置说明](../../../mcp/README.md) 安装并配置官方服务及 Agent Key，勿把密钥提交到仓库。技能不包含服务、账号或密钥；接入后先让 Agent 调用 `get_schema`，再开始复盘或制定计划。游标由 Agent 自己保存。判断阈值是草案，见 [判断标准](references/thresholds.md)，可由用户覆盖。


## 本机安装步骤与核实范围

以下从本仓库根目录执行，复制整个目录以保留引用；复制前如目标已存在，请先检查，避免覆盖自己的修改。

Claude Code 个人技能目录：

```bash
mkdir -p ~/.claude/skills
cp -R agent_skills/jikeyan-academic-colleague ~/.claude/skills/
```

Codex 个人技能目录：

```bash
mkdir -p ~/.codex/skills
cp -R agent_skills/jikeyan-academic-colleague ~/.codex/skills/
```

本机可核实 Codex 的 `~/.codex/skills/`，项目规则也使用 `.agents/skills/`；Claude Code 的技能目录及客户端刷新行为在本机待核实。上述命令仅复制技能，不注册 MCP。请按仓库 MCP 说明配置本机 stdio 服务和 Agent Key，再用客户端的 MCP 列表检查；Codex 可用 `codex mcp list`。启动新会话后明确请求使用本技能并调用 `get_schema`，若没有发现技能或工具，检查客户端配置与服务进程；不要将 Key 提交到仓库。具体客户端自动发现和刷新时机待核实。

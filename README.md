# jikeyan-agent skill

一个公开的 Agent Skill（Claude Code / Codex 兼容的 `SKILL.md` 格式），教 agent
通过 Agent API 读写**极科研 (jikeyan)** 的课题、节点、等待项和投稿记录。

## 安装

把 `jikeyan-agent/` 整个目录复制到 skills 目录即可：

```bash
cp -r jikeyan-agent ~/.claude/skills/   # Claude Code
cp -r jikeyan-agent ~/.codex/skills/    # Codex
```

## 使用

调用前先设置 key（与 agent 账号绑定的 Agent Key）：

```bash
export JIKEYAN_API_KEY='<agent key>'
export JIKEYAN_API_BASE='https://api.jikeyan.cn'   # 可选，默认值即此
```

然后按 `SKILL.md` 的流程操作（先 `GET /agent/schema`，读->写携带版本号）。
也可以直接用附带的 curl 封装：

```bash
jikeyan-agent/scripts/jikeyan.sh get /api/v1/agent/schema
```

## 安全说明

- Key 只从环境变量 `JIKEYAN_API_KEY` 读取，**不要写死、不要提交、不要贴到聊天记录或日志里**。
- **不要向 API 发送患者姓名、住院号、诊断或随访原文**——接口本来就没有这些字段，未知字段会被拒绝。
- 本仓库不含任何 key、token、账号信息；`JIKEYAN_API_BASE` 默认指向公开 API 地址。

## 协议

MIT，见 [LICENSE](LICENSE)。

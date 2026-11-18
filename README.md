# jikeyan-agent-skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP: stdio](https://img.shields.io/badge/MCP-stdio-blue)](mcp/README.md)

**Official agent skills + MCP server for [极科研 (jikeyan)](https://jikeyan.cn) — let your AI agent manage research projects, deadlines, waiting items, submissions, and review rounds.**

极科研 (jikeyan) is a local-first iOS kanban app for research project tracking.
This repo is its official agent entry point: two installable skills and a
standalone MCP server, all speaking to the same documented Agent API
([online guide](https://api.jikeyan.cn/agent.md)).

> 中文说明见 [README.zh-CN.md](README.zh-CN.md)。

## What your agent can do

Everything below maps to a real skill workflow or MCP tool — no mockups:

1. **Morning brief** — overdue nodes, items due in 7 days, waiting items to re-check today, and the last 48h of updates (`get_today` + daily-review workflow).
2. **Chase waiting items** — find stalled "waiting on someone" items and draft bilingual follow-up messages (you send them yourself; the agent never contacts anyone).
3. **Bulk-import projects** — create projects idempotently via your own `external_ref`, then add nodes in one versioned patch.
4. **Break down reviewer comments** — split review comments into numbered action items, draft the point-by-point response letter, record the round (`add_review_round`).
5. **Pre-submission checklist** — journal requirements, ethics, authorship, references, figures, cover letter, one item at a time.
6. **Deadline countdown** — plan backwards from a hard date with buffers for external feedback and co-author confirmation.
7. **Verify references & screen topics** — check BibTeX metadata against Crossref/PubMed, and screen ClinicalTrials.gov + PubMed reviews for topic collisions (runs locally, never touches the jikeyan server).
8. **Weekly review** — what got done, what's due next, what's stalled, what needs your decision.

## Quickstart (3 steps)

**1. Generate a key** — in the 极科研 app: **设置 → 连接智能体** (Settings → Connect Agent), generate an Agent Key.

**2. Export it** — the key lives only in your environment, never in a repo:

```bash
export JIKEYAN_AGENT_KEY='<your agent key>'
```

**3. Install the skill or the MCP server** — pick one row:

| Client | Skill | MCP server |
|---|---|---|
| Claude Code | `/plugin marketplace add 871922384/jikeyan-agent-skill` then `/plugin install jikeyan@jikeyan` (or copy `plugins/jikeyan/skills/*` to `~/.claude/skills/`) | `.mcp.json` snippet below |
| Codex | copy `plugins/jikeyan/skills/*` to `~/.codex/skills/` | `codex mcp add …` snippet below |
| Cursor / Windsurf / other MCP clients | copy `plugins/jikeyan/skills/*` to the client's skills dir | generic stdio config below |

After installing, ask your agent to "use the jikeyan skill and run `get_schema` first".

### MCP config snippets

Claude Code `.mcp.json` (project-level; keep it uncommitted if it holds your key):

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

Codex:

```bash
codex mcp add jikeyan \
  --env JIKEYAN_AGENT_KEY="$JIKEYAN_AGENT_KEY" \
  --env JIKEYAN_API_BASE_URL=https://api.jikeyan.cn \
  -- uvx jikeyan-mcp
```

Other clients (Cursor, Windsurf, Gemini CLI…): add a stdio server with command
`uvx`, args `["jikeyan-mcp"]`, and the two environment variables above.
`uvx jikeyan-mcp` needs the `jikeyan-mcp` package on PyPI; until then use:

```bash
uvx --from "jikeyan-mcp @ git+https://github.com/871922384/jikeyan-agent-skill#subdirectory=mcp" jikeyan-mcp
```

Plain-HTTP alternative (no MCP): `plugins/jikeyan/skills/jikeyan-agent/scripts/jikeyan.sh`
is a curl wrapper around the same API — `JIKEYAN_AGENT_KEY` + `get/post/patch`.

## Contents

| Path | What it is |
|---|---|
| `plugins/jikeyan/skills/jikeyan-agent/` | Skill: Agent API cookbook + `jikeyan.sh` curl wrapper + endpoint table |
| `plugins/jikeyan/skills/jikeyan-academic-colleague/` | Skill: research-management workflows (daily/weekly review, stalled detection, waiting-item follow-up, review response, pre-submission, backward planning) |
| `mcp/` | Standalone Python package `jikeyan-mcp` (17 MCP tools, stdio). See [mcp/README.md](mcp/README.md) |
| `.claude-plugin/marketplace.json` | Claude Code plugin marketplace清单 |
| `server.json` | Official MCP Registry清单 (prepared, not yet submitted) |
| `smithery.yaml` | Smithery deploy config (prepared, not yet submitted) |
| `llms.txt` | LLM-readable repo summary |
| `docs/distribution.md` | Format sources, suggested repo metadata, manual submission checklist |

## Security & privacy

- The Agent Key is read from the environment (`JIKEYAN_AGENT_KEY`) only. Never hard-code it, never commit it, never paste it into chat logs.
- **Never send patient names, hospital IDs, diagnoses, or follow-up text.** The API has no fields for them and rejects unknown fields — keep it that way. Personal notes stay on your device and are never synced.
- The MCP server runs on your own machine; it logs only tool names and HTTP status codes — no keys, no content.
- Key permissions (read-only, project-scoped) are enforced server-side. A revoked key returns `401`: regenerate it in the app.

## Links

- 极科研: [https://jikeyan.cn](https://jikeyan.cn) · [App Store](https://apps.apple.com/app/id6785017540) · [Privacy](https://jikeyan.cn/privacy)
- Agent API online guide: [https://api.jikeyan.cn/agent.md](https://api.jikeyan.cn/agent.md)
- MCP package: [mcp/README.md](mcp/README.md)

## License

MIT, see [LICENSE](LICENSE).

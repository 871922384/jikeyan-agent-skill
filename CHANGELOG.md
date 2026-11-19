# Changelog

## Unreleased

Welcome openings now cover zero counts with a 5-way rule instead of 2-way:
`project_count == 0` → `opening_empty`; overdue and waiting both present →
`opening`; no overdue but waiting → `opening_no_overdue`; overdue but no
waiting → `opening_no_waiting`; neither → `opening_clear` (overdue =
`today.overdue` length, waiting = `today.waiting_to_check` length). New
`opening_no_overdue` / `opening_no_waiting` / `opening_clear` copy (zh/en)
lands in `schema.welcome`, the bundled fallback
`plugins/jikeyan/skills/jikeyan-agent/references/welcome.md`, both skills'
first-conversation rules, and the `jikeyan_welcome` MCP prompt; tests pin the
approved copy verbatim (placeholders per variant, no hardcoded `0 项`).

## 0.2.1 — 2026-11-18

First conversation now feels like a product, not a manual. `GET /api/v1/agent/schema`
is expected to return `welcome` (zh/en: `opening`, `opening_empty`,
`capabilities`, `suggestions`, `tone`, placeholders `{project_count}`
`{overdue_count}` `{waiting_today_count}`); both skills silently call
schema → today → projects, greet in the user's language, list capabilities, and
offer 3 suggestions — never reciting endpoints or mentioning keys unasked.

### Skills

- `jikeyan-agent` / `jikeyan-academic-colleague`: new "First conversation /
  第一次对话" rule (silent reads → `schema.welcome` → localized opening +
  capabilities + 3 suggestions → obey `tone`); body reordered role-first
  (who-you-are → workflows → interface/compliance details); product-style
  `description` keeps all trigger words.
- New `jikeyan-agent/references/welcome.md`: bundled fallback copy (same
  structure/placeholders as the server `welcome`) used when the server does
  not return `welcome` yet; `academic-colleague/references/onboarding.md`
  points at it.

### MCP server (`jikeyan-mcp` 0.2.1)

- Server instructions add the short greeting rule; new `jikeyan_welcome`
  prompt (`mcp/src/jikeyan_mcp/prompts.py`) returns the opening flow for
  pure-MCP clients without the skill files. Tests: 20 passed (17 existing + 3 new).

### Docs

- `README.md` / `README.zh-CN.md`: "What the first conversation looks like /
  第一次对话长这样" demo dialogue (demo data only) next to the capabilities table.


## 0.2.0 — 2026-11-18

Public packaging release: the repo becomes the official agent entry point for
极科研 (jikeyan). No third-party submissions were made from this branch; all
registry/awesome-list filings are left for the maintainer (see
`docs/distribution.md`).

### Skills

- `jikeyan-agent`: aligned with the live API (`app/static/agent.md` +
  `app/api/v1/external_agent.py` on jikeyan-api main, verified against
  https://api.jikeyan.cn/agent.md). Auth env `JIKEYAN_API_KEY` →
  `JIKEYAN_AGENT_KEY`; 课题 → 项目; added `GET /agent/changes`, `dry_run`
  on writes, 401/429 handling. `jikeyan.sh` accepts the new var and keeps the
  old name as a deprecated fallback with a stderr warning.
- Added `jikeyan-academic-colleague`: daily/weekly review, stalled detection,
  waiting-item follow-up, review response, pre-submission checks, backward
  planning. Copied from jikeyan-api `agent_skills/`; reviewed — no private
  info; cross-links fixed to the new layout.
- Both skills ship under `plugins/jikeyan/skills/` so the Claude Code
  marketplace plugin can serve them from one directory.

### MCP server (`mcp/`, package `jikeyan-mcp`)

- Standalone installable package vendored from jikeyan-api `mcp_server` +
  `capability_tools` (vendored as `jikeyan_mcp.local_search`, stdlib-only).
  No imports of jikeyan-api internals remain.
- Entry points: `jikeyan-mcp` console script, `python -m jikeyan_mcp`,
  `uvx jikeyan-mcp`; default base URL `https://api.jikeyan.cn`.
- Docs scrubbed of staging-port notes and private-repo paths; privacy notice
  kept on every tool.
- Minimal offline tests (17 passed): config, HTTP client envelope mapping,
  tool inventory/annotations, write-path wiring via fake transports.

### Docs & distribution (prepared, not submitted)

- `README.md` (EN first) + `README.zh-CN.md`: value prop, 8 verified
  capabilities, 3-step setup, Claude Code/Codex/Cursor snippets, security.
- `llms.txt`, `.claude-plugin/marketplace.json`,
  `plugins/jikeyan/.claude-plugin/plugin.json`, `plugins/jikeyan/.mcp.json`,
  `server.json` (MCP Registry, PyPI), `smithery.yaml`,
  `docs/distribution.md` (format sources, repo meta suggestions, manual
  submission checklist for PyPI → Registry → Smithery → Glama → awesome lists).

### CI

- `.github/workflows/checks.yml`: SKILL.md frontmatter + manifest JSON checks,
  shellcheck, MCP pytest on Python 3.11/3.12.

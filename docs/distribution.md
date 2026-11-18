# 分发说明（distribution）

本仓库所有对外清单文件都已准备好，但**需要 Rex 手动提交**——本分支不做任何
第三方平台发布（npm / PyPI / MCP Registry / awesome 列表 PR 等一律不做）。

## 1. 清单文件格式出处（已联网核实，2026-11-18）

| 文件 | 格式依据 | 出处 URL |
|---|---|---|
| `.claude-plugin/marketplace.json` | Claude Code《Create a marketplace》：顶层 `name` + `owner` + `plugins[]`，entry 需 `name` + `source`（本仓库用相对路径 `./plugins/jikeyan`），entry 名须与 `plugin.json` 的 `name` 一致 | https://code.claude.com/docs/en/plugin-marketplaces.md |
| `plugins/jikeyan/.claude-plugin/plugin.json` | Claude Code《Plugin manifest reference》：`name` 必填（kebab-case），`version`/`description`/`author` 缺失会报 warning；`mcpServers` 等组件路径须在插件目录内 | https://code.claude.com/docs/en/plugins/manifest-reference.md |
| `plugins/jikeyan/.mcp.json` | 同上：插件根目录 `.mcp.json` 会自动加载为 MCP 服务定义，`command: uvx + args: [jikeyan-mcp]` | https://code.claude.com/docs/en/plugins/manifest-reference.md |
| `server.json` | MCP Registry《server.json Format Specification》+《Official Registry Requirements》+《Package Types》：`$schema` 固定为 `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`；`description` ≤ 100 字符（本文件 83）；PyPI 包用 `registryType: pypi` + `registryBaseUrl: https://pypi.org`；PyPI 所有权验证靠包 README（含 PyPI 描述页）里的 `mcp-name: <server-name>` 字符串（已写入 `mcp/README.md` 首部注释） | https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md · https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md · https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx · 发布流程 https://modelcontextprotocol.io/registry/quickstart |
| `smithery.yaml` | Smithery stdio 部署格式：`startCommand.type: stdio` + `configSchema`（JSON Schema）+ `commandFunction`（`(config) => ({command, args, env})`）。本文件 `uvx jikeyan-mcp`，全部配置项可选 | https://smithery.ai （registry）及已部署的 stdio 范例；配置参考入口 https://smithery.ai/docs |
| `llms.txt` | llms.txt v2 提案：H1 项目名 + blockquote 摘要 + H2 文件列表（含链接与说明） | https://llmstxt.org/ |

> 说明：smithery.ai 文档站是 JS 渲染，`curl`/纯文本抓取返回 404，格式以上是对照
> registry 公开文档与多个已部署仓库的 `smithery.yaml` 交叉验证的（`startCommand` /
> `configSchema` / `commandFunction` 三件套一致）。提交前请在 Smithery 网站表单里再对一遍。

## 2. 仓库元信息建议（给 Rex：合并后在 GitHub 网页上设置，不要 `gh repo edit`）

- **Description（EN）**：`Official agent skills + MCP server for 极科研 (jikeyan): let your AI agent manage research projects, deadlines, reviews and submissions.`
- **Description（CN，如需中文）**：`极科研官方 Agent 技能与 MCP 服务：让 AI 智能体帮你管理科研项目、节点、等待项、投稿与审稿。`
- **Homepage**：`https://jikeyan.cn`
- **Topics（20 个）**：
  `mcp` `mcp-server` `model-context-protocol` `claude-skills` `agent-skills`
  `claude-code` `codex` `cursor` `agents`
  `research-management` `research` `academic` `kanban`
  `phd` `paper-writing` `systematic-review` `clinical-research`
  `productivity` `ios` `chinese`

## 3. 需要 Rex 亲自提交的平台清单与步骤

顺序建议：先 **PyPI**（它是 MCP Registry 与 `uvx` 的前置），再各目录。

### 3.1 PyPI：`jikeyan-mcp`（前置）

1. 在 https://pypi.org 注册账号并开启 2FA。
2. 本地打 tag 后构建发布（需先 `pip install build twine`）：
   ```bash
   git checkout main && git pull
   cd mcp && python -m build && twine upload dist/jikeyan-mcp-0.2.0*
   ```
3. 验证：`uvx jikeyan-mcp --help` 在一台干净机器上能跑（会提示缺 key 并退出码 1，属于正常）。
4. 注意：包 README（即 PyPI 描述页）首部已有 `<!-- mcp-name: io.github.871922384/jikeyan-agent-skill -->`，
   这是 MCP Registry PyPI 所有权验证的依据，**不要删**。

### 3.2 官方 MCP Registry

- 指南：https://modelcontextprotocol.io/registry/quickstart
- 步骤：`npm install -g mcp-publisher`（或按官方最新方式安装）→ `mcp-publisher login github` →
  在仓库根目录 `mcp-publisher publish`（读取本仓库 `server.json`）→
  用 `curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.871922384/jikeyan-agent-skill"` 验证。
- 前置：PyPI 包已发布且版本号与 `server.json` 的 `version` 一致（当前 `0.2.0`）；
  `name` 命名空间 `io.github.871922384` 需用同名 GitHub 账号登录验证。
- Registry 目前为 preview，提示 breaking change / 数据重置属正常。

### 3.3 Smithery

- 在 https://smithery.ai 用 GitHub 登录 → Add Server → 填本仓库地址，选择 Python/stdio，
  按网站表单核对 `smithery.yaml`（命令 `uvx jikeyan-mcp`，配置项全可选）。
- 前置：PyPI 包已发布。

### 3.4 Glama

- 打开 https://glama.ai/mcp/servers → Add MCP Server → 填 GitHub 仓库 URL、名称与简介，
  用有写权限的 GitHub 账号登录。Glama 会做自动检查（license 识别、安全扫描、健康测试），
  多数几分钟内通过并可搜索到。参考：https://glama.ai/mcp/faq
- 可选：在仓库根加 `glama.json`（`{"$schema": "https://glama.ai/mcp/schemas/server.json", "maintainers": ["<github-username>"]}`）
  声明维护人；本仓库暂未加，如 Glama 要求再补。
- 注意：Glama 从源码构建运行服务，可能要求仓库有可构建的服务形态；当前 `mcp/` 是
  `uvx`-from-PyPI 形态，若 Glama 构建失败，可补一个最小 `Dockerfile` 再试。

### 3.5 mcpservers.org（wong2/awesome-mcp-servers 的提交入口）

- 该列表**不收 PR**，去 https://mcpservers.org/submit 提交（README 顶部注明）。
  参考：https://github.com/wong2/awesome-mcp-servers

### 3.6 其他 awesome /skills 目录（按活跃度排序，需逐个按其 CONTRIBUTING 提交 PR）

- https://github.com/ComposioHQ/awesome-claude-skills （stars 最多，skill 发现主入口）
- https://github.com/punkpeye/awesome-mcp-servers （老牌 MCP 列表）
- https://github.com/TensorBlock/awesome-mcp-servers （带 hosted index，可顺手认领 profile）
- https://awesomeclaudeskills.com/submit （awesome-claude-skills 目录站的提交表单，人工审核）
- https://github.com/travisvn/awesome-claude-skills （提交指南见其 README / `someclaudeskills` 的 registry-submission-guides）
- Glama 徽章：上架后可把 Glama listing 徽章加回 README（当前未加，避免指向不存在的页面）。

### 3.7 Claude Code 插件市场生效方式

- 用户侧：`claude plugin marketplace add 871922384/jikeyan-agent-skill`，
  然后 `claude plugin install jikeyan@jikeyan`。无需向 Anthropic 提交任何东西；
  如需进官方 directory，另走 https://code.claude.com/docs/en/plugins/publish.md 的
  "Submit to Anthropic's directory" 流程（需 Rex 手动申请）。
- 验证方式：`claude plugin validate ./`（需安装 Claude Code CLI；CI 里只做 JSON 结构检查）。

## 4. 发版顺序 checklist（给 Rex）

1. 合并 `feat/packaging` 到 `main`。
2. 在 GitHub 网页设置 description / homepage / topics（见 §2）。
3. 发 PyPI `jikeyan-mcp 0.2.0`（§3.1），验证 `uvx jikeyan-mcp`。
4. 发官方 MCP Registry（§3.2）。
5. Smithery（§3.3）、Glama（§3.4）、mcpservers.org（§3.5）。
6. awesome PR 若干（§3.6）。

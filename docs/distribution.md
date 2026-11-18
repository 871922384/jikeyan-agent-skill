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

## 5. 社交预览图上传步骤（给 Rex：合并后在 GitHub 网页上设置）

仓库已备好 `assets/social-preview.png`（1280×640，品牌深色渐变 `#0F2027→#203A43` +
App Icon + 中英文 tagline，用 PIL 生成，见下方生成命令备查）。GitHub 不会自动用它，
需手动上传：

1. 打开 `https://github.com/871922384/jikeyan-agent-skill` → **Settings** → **General**。
2. 拉到 **Social preview** → **Upload an image…** → 选择 `assets/social-preview.png`。
3. 保存后发一条带链接的推文/即刻验证缓存刷新（GitHub 卡片缓存最长一周）。

重新生成（品牌色/文案改了才需要）：

```bash
python3 - <<'EOF'
# 见 feat/packaging 分支提交历史：PIL 渐变 + PingFang SC(Index 3) + assets/logo.png
EOF
```

生成脚本以本次提交的 `assets/social-preview.png` 为准，字体用系统 PingFang SC，
Linux CI 上如缺中文字体需先装 Noto Sans CJK 再跑。

## 6. 只支持远程 MCP 的平台：现状与托管选项（不部署，只给方案）

背景：扣子 Coze、Kimi 托管智能体、智谱 Managed Agents、百炼 Flow 智能体（自定义 MCP 的
`http` 注册形态）都**不能跑用户本机的 stdio 进程**，只接受公网 HTTPS 的
SSE / Streamable HTTP 端点。`jikeyan-mcp` 目前是 stdio 包，要上这些平台必须先有一层
远程托管。本仓库**不部署任何服务**，以下只列选项与工作量，供 Rex 决策：

| 选项 | 怎么做 | 费用/工作量 | 适合 |
|---|---|---|---|
| A. 百炼自定义 MCP → 脚本部署 | 把 stdio 包（`npx`/`uvx`）托管到函数计算 FC，按官方文档走“脚本部署” | 基础模式按调用时长约 0.000156 元/秒、无部署费；极速模式另收部署费约 0.000036 元/秒；工作量半天 | 已在用百炼智能体应用时最顺 |
| B. 魔搭 MCP 广场托管 | PyPI 发 `jikeyan-mcp` 后在 `modelscope.cn/mcp/servers/create` 选“可托管部署”，平台自动托管并给专属 SSE URL | 免费额度内验证；工作量半天（含 PyPI 发包，见 §3.1） | 想同时进魔搭生态、被灵码/Kimi 一键接入 |
| C. 自有服务器/VPS 常驻进程 | 在自己的云主机上跑 Streamable HTTP 版 `jikeyan-mcp`（需给包加一个 HTTP 传输入口，约半天开发量）+ 域名 + Bearer 鉴权 | 一台轻量云主机/月；工作量 1–2 天（含 HTTP 入口开发） | 要完全自主可控、长期运营 |

注意：托管后 Agent Key 的传递方式要重新设计（stdio 是读本机环境变量，远端必须走
Vault/请求头注入，绝不能把 key 写进公开配置），动手前先定鉴权方案。

## 7. 国内平台上架清单（只准备材料，不提交）

核实日期均为 2026-11-18；“未核实”= 翻遍官方文档没找到公开口径，不得当作承诺。

| 平台 | 提交入口 | 所需材料 | 企业认证 | 状态 |
|---|---|---|---|---|
| 魔搭 ModelScope MCP 广场 | `https://modelscope.cn/mcp/servers/create?template=customize`（也支持从 GitHub 仓库创建） | 中英文名称、来源地址、MCP 配置 + 环境变量、完整 README；选“可托管部署”需先发 PyPI 包（`pyproject.toml` 含 `[project.scripts]` 入口） | 未核实（官方只要求注册登录 + 访问令牌） | 可备材料，待 PyPI 发包后提交 |
| 百炼 OneKey MCP（云市场商品） | 云市场服务商控制台 → 商品管理 → 接入信息 → 接入类型选 OneKey MCP | MCP 协议链接（SSE/StreamableHttp 二选一）+ 鉴权 `Authorization` + SPI 接口（实例创建/过期/释放必选）+ `tools/list` 自测 + 商品信息（Logo、简介、≥2 条亮点、详情 4 模块、使用指南 PDF≤10M）+ 按量销售信息（credits 体验包总量 ≥1000）+ 计量出账自测证明 | 未核实（前提是“完成云市场服务商入驻”；且 OneKey 上架为**邀约制**） | 材料重，先观望邀约 |
| 腾讯云 MCP 广场 | 无 | —— | —— | **不支持**：官方明确暂不提供第三方上架 |
| 扣子 Coze 插件商店 | 开发平台 → 更多 → 社区 → 插件市场 → 上架插件；企业商店走工作空间上架 | 描述/使用说明/分类；基于 MCP 的插件要求 HTTPS 域名 URL（不支持裸 IP） | 个人上架公共商店是否需企业认证：未核实；企业商店需企业旗舰版 | 需先有远程 MCP 端点（见 §6） |
| Kimi 开放平台 | 未核实公开上架入口（自定义技能/插件仅项目内可见） | —— | 未核实 | 观望 |
| 智谱开放平台 | 未核实公开上架入口（控制台技能市场仅“查看并安装”） | —— | 未核实 | 观望 |
| 字节 Trae 市场 | 未核实上架入口与审核要求（企业版有“企业技能”管理） | —— | 未核实 | 观望 |
| 腾讯 CodeBuddy 插件市场 | 自建市场仓库 + `plugin.json`（`name/description/version/author` 必备）+ README + 安全自查；用户侧 `/plugin marketplace add <owner/repo>` | 完整 `plugin.json` + README | 未核实 | 可备材料（本仓库插件结构已就绪） |

通用备料（现在就能准备、不依赖任何平台）：`assets/logo.png`（1024 官方 App Icon）、
`assets/screenshots/*.png`（3 张演示数据截图）、中英文简介各一段（见仓库 Description 建议 §2）、
MIT LICENSE、PyPI 包 `jikeyan-mcp 0.2.0`（它是魔搭/百炼托管的前置）。

## 8. 发版顺序 checklist（给 Rex）

1. 合并 `feat/packaging` 到 `main`。
2. 在 GitHub 网页设置 description / homepage / topics（见 §2）+ 上传社交预览图（见 §5）。
3. 发 PyPI `jikeyan-mcp 0.2.0`（§3.1），验证 `uvx jikeyan-mcp`。
4. 发官方 MCP Registry（§3.2）。
5. Smithery（§3.3）、Glama（§3.4）、mcpservers.org（§3.5）。
6. awesome PR 若干（§3.6）。
7. 国内：PyPI 发包后视情况备料魔搭 MCP 广场（§7）；远程 MCP 托管方案（§6）按需决策。

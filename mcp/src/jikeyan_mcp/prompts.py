"""First-conversation prompt: greet the user like a product, not a manual.

The full copy lives in the skill repo
(``plugins/jikeyan/skills/jikeyan-agent/references/welcome.md``) and,
once shipped, in ``GET /api/v1/agent/schema`` under ``welcome``.
This prompt only teaches the flow so the agent asks for it even when the
skill files are not installed (pure-MCP clients).
"""

from __future__ import annotations

from typing import Any

WELCOME_PROMPT_NAME = "jikeyan_welcome"

WELCOME_PROMPT_DESCRIPTION = (
    "第一次对话开场流程：静默摸底后按用户语言说开场白、列能力、给 3 条建议。"
)

WELCOME_FALLBACK_PATH = (
    "plugins/jikeyan/skills/jikeyan-agent/references/welcome.md"
)


def welcome_prompt_text() -> str:
    """The flow returned by the ``jikeyan_welcome`` MCP prompt."""
    return (
        "第一次对话（First conversation）：你刚接手用户的极科研看板，先开场、再干活。\n"
        "1. 静默摸底：依次调用 get_schema → get_today → list_projects，不要念给用户听。\n"
        "2. 选文案：用 get_schema 返回的 welcome（zh/en：opening、opening_empty、"
        "capabilities、suggestions、tone）；若服务端尚未返回 welcome，用 skill 仓库内"
        f"置的同一份文案兜底（{WELCOME_FALLBACK_PATH}）。\n"
        "3. 说开场白：按用户语言填好占位符（{project_count} {overdue_count} "
        "{waiting_today_count}，数字来自第 1 步的真实返回）说 opening；看板为空时用 "
        "opening_empty。然后列出能力（capabilities），再给 3 条具体建议（suggestions），"
        "等用户挑。\n"
        "4. 遵守 tone：专业、温和、干练，直奔主题；主动列出该推进的节点和在等的回音；"
        "绝不索取患者信息；删除、归档前先确认；不提工具、密钥、技术细节（用户问起再答）。"
    )


def register_prompts(server: Any) -> None:
    """Register the first-conversation prompt on a FastMCP server."""

    @server.prompt(name=WELCOME_PROMPT_NAME, description=WELCOME_PROMPT_DESCRIPTION)
    async def jikeyan_welcome() -> str:
        return welcome_prompt_text()

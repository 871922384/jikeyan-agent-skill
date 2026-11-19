"""Environment configuration for the MCP server.

Only two things are configurable:

- ``JIKEYAN_API_BASE_URL``: the root of the 极科研 API. Defaults to the
  production API at ``https://api.jikeyan.cn``.
- ``JIKEYAN_AGENT_KEY``: the Agent Key used as ``Authorization: Bearer <key>``.

Nothing is written to disk and the key is never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

#: Production API root.
DEFAULT_BASE_URL = "https://api.jikeyan.cn"

#: Environment variable names.
ENV_BASE_URL = "JIKEYAN_API_BASE_URL"
ENV_AGENT_KEY = "JIKEYAN_AGENT_KEY"

#: The agent API prefix; every tool path is appended to it.
AGENT_API_PREFIX = "/api/v1/agent"

#: Guard rail: the server refuses to run against a base URL that does not look
#: like an HTTP(S) origin.
_ALLOWED_SCHEMES = ("http://", "https://")


class ConfigError(RuntimeError):
    """Raised when the MCP server cannot start because of its configuration."""


@dataclass(frozen=True)
class Config:
    """Resolved configuration for one MCP server process."""

    base_url: str
    agent_key: str

    @property
    def api_root(self) -> str:
        """``base_url`` without a trailing slash."""
        return self.base_url.rstrip("/")


def _clean_base_url(raw: str) -> str:
    value = raw.strip().rstrip("/")
    if not value:
        raise ConfigError(
            f"{ENV_BASE_URL} 为空：请设置 API 根地址，例如 https://api.jikeyan.cn"
        )
    if not value.startswith(_ALLOWED_SCHEMES):
        raise ConfigError(
            f"{ENV_BASE_URL} 必须以 http:// 或 https:// 开头，当前为：{value}"
        )
    return value


def load_config(env: dict[str, str] | None = None) -> Config:
    """Build a :class:`Config` from the environment.

    Raises :class:`ConfigError` with an actionable message when the Agent Key
    is missing. The key value itself is never part of the message.
    """
    source = os.environ if env is None else env
    raw_base = source.get(ENV_BASE_URL) or DEFAULT_BASE_URL
    base_url = _clean_base_url(raw_base)
    agent_key = (source.get(ENV_AGENT_KEY) or "").strip()
    if not agent_key:
        raise ConfigError(
            f"缺少环境变量 {ENV_AGENT_KEY}：请先在 App 内生成 Agent Key，"
            f"再把它导出为 {ENV_AGENT_KEY} 后重启 MCP 服务。"
        )
    return Config(base_url=base_url, agent_key=agent_key)

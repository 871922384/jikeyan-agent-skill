"""极科研官方 MCP 服务（用户本机运行的 stdio 进程）。

只通过 HTTP 调用现有 ``/api/v1/agent/*`` 接口；不绕过鉴权、不直连数据库、
不 import 服务端的 service/model 层。工具按意图命名；工具描述里的字段上限
与枚举来自 ``GET /agent/schema`` 的运行时结果。不接收患者姓名、住院号、
诊断或随访文本（服务端规则，MCP 不放宽）。

本包是 jikeyan-api 私有仓库内 ``mcp_server`` + ``capability_tools`` 的
独立可安装版本：只依赖公开 PyPI 包，可用 ``uvx jikeyan-mcp`` 直接运行。
"""

from __future__ import annotations

__all__ = ["__version__", "build_server"]

__version__ = "0.2.0"


def build_server(*args, **kwargs):
    """Lazy re-export of :func:`jikeyan_mcp.server.build_server`.

    The import is deferred so that ``import jikeyan_mcp`` does not require
    ``fastmcp`` to be installed (it is a required dependency of the
    ``jikeyan-mcp`` distribution, but not needed for e.g. version checks).
    """
    from jikeyan_mcp.server import build_server as _build_server

    return _build_server(*args, **kwargs)

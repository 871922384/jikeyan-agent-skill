# jikeyan-mcp — 极科研官方 MCP 服务（stdio）
#
# 构建（仓库根目录）：
#   docker build -f mcp/Dockerfile -t ghcr.io/871922384/jikeyan-mcp:<version> ./mcp
# 运行（Key 只从运行时环境变量读，镜像里不含任何密钥）：
#   docker run -i --rm -e JIKEYAN_AGENT_KEY ghcr.io/871922384/jikeyan-mcp:<version>
#
# 构建参数 VERSION 仅用于镜像 label 记录版本，不影响运行。

FROM python:3.12-slim-bookworm

ARG VERSION=0.0.0-dev

# MCP Registry OCI 所有权验证：值必须与 server.json 的 name 完全一致。
# 出处：https://modelcontextprotocol.io/registry/package-types（Docker/OCI Images 一节）
LABEL io.modelcontextprotocol.server.name="io.github.871922384/jikeyan-agent-skill" \
      org.opencontainers.image.title="jikeyan-mcp" \
      org.opencontainers.image.source="https://github.com/871922384/jikeyan-agent-skill" \
      org.opencontainers.image.version="${VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先只复制打包元信息，利用层缓存；源码变更不使依赖层失效。
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10000 --user-group appuser \
    && python -c "import jikeyan_mcp.server" \
    && rm -rf /root/.cache

USER appuser

ENTRYPOINT ["jikeyan-mcp"]

#!/usr/bin/env bash
# Minimal curl wrapper for the 极科研 (jikeyan) Agent API.
#
# Usage:
#   jikeyan.sh get <path>
#   jikeyan.sh post <path> [json-body]
#   jikeyan.sh patch <path> [json-body]
#
# Env:
#   JIKEYAN_AGENT_KEY       (required) agent key, sent as a Bearer token.
#                         The old name JIKEYAN_API_KEY is still accepted as a
#                         fallback but is deprecated and will be removed.
#   JIKEYAN_API_BASE        (optional) default https://api.jikeyan.cn
#   JIKEYAN_IDEMPOTENCY_KEY (optional) sent as Idempotency-Key on post/patch.
#
# Examples:
#   jikeyan.sh get /api/v1/agent/schema
#   jikeyan.sh get "/api/v1/agent/today?tz=Asia%2FShanghai"
#   jikeyan.sh post /api/v1/agent/projects '{"title":"...","template_id":"paper"}'
set -euo pipefail

fail() {
  printf 'jikeyan.sh: %s\n' "$1" >&2
  exit "${2:-1}"
}

command -v curl >/dev/null 2>&1 || fail "curl is required but not installed."

if [ -n "${JIKEYAN_AGENT_KEY:-}" ]; then
  AGENT_KEY="${JIKEYAN_AGENT_KEY}"
elif [ -n "${JIKEYAN_API_KEY:-}" ]; then
  printf 'jikeyan.sh: warning: JIKEYAN_API_KEY is deprecated, use JIKEYAN_AGENT_KEY instead.\n' >&2
  AGENT_KEY="${JIKEYAN_API_KEY}"
else
  fail "JIKEYAN_AGENT_KEY is not set. Export your agent key first; never hard-code it."
fi

BASE="${JIKEYAN_API_BASE:-https://api.jikeyan.cn}"
METHOD="${1:-}"
PATH_ARG="${2:-}"
BODY="${3:-}"

case "$METHOD" in
  get | post | patch) ;;
  *) fail "usage: jikeyan.sh get|post|patch <path> [json-body]" 2 ;;
esac

if [ -z "$PATH_ARG" ]; then
  fail "usage: jikeyan.sh get|post|patch <path> [json-body]" 2
fi

UPPER=$(printf '%s' "$METHOD" | tr '[:lower:]' '[:upper:]')

ARGS=(-sS -H "Authorization: Bearer ${AGENT_KEY}")
if [ "$UPPER" != "GET" ]; then
  ARGS+=(-H "Content-Type: application/json")
  if [ -n "${JIKEYAN_IDEMPOTENCY_KEY:-}" ]; then
    ARGS+=(-H "Idempotency-Key: ${JIKEYAN_IDEMPOTENCY_KEY}")
  fi
fi

if [ -n "$BODY" ]; then
  curl "${ARGS[@]}" -X "$UPPER" -d "$BODY" -w '\nHTTP_STATUS:%{http_code}\n' -- "${BASE}${PATH_ARG}"
else
  curl "${ARGS[@]}" -X "$UPPER" -w '\nHTTP_STATUS:%{http_code}\n' -- "${BASE}${PATH_ARG}"
fi

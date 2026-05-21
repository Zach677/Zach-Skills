#!/usr/bin/env bash
# SessionStart hook: detect project .env and emit an additionalContext hint
# listing the available keys (names only; values are never echoed).
set -euo pipefail

if ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  PROJECT_DIR="$ROOT"
else
  PROJECT_DIR="${CODEX_PROJECT_DIR:-$PWD}"
fi

ENV_FILE="$PROJECT_DIR/.env"

[ -r "$ENV_FILE" ] || exit 0

keys=$(
  grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=' "$ENV_FILE" \
    | sed -E 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*).*$/\1/' \
    | sort -u \
    | paste -sd, -
)

[ -n "$keys" ] || exit 0

count=$(echo "$keys" | tr ',' '\n' | wc -l | tr -d ' ')

jq -n \
  --arg keys "$keys" \
  --arg count "$count" \
  --arg file "$ENV_FILE" '
{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: (
      "Project .env detected at `" + $file + "` with " + $count + " key(s): " + $keys + ".\n" +
      "Values are NOT auto-injected into the Codex process env. " +
      "When a shell command needs them, prefix with: `set -a && source .env && set +a && <your-command>`."
    )
  }
}'

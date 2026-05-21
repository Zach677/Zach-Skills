#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
  echo "usage: $(basename "$0") <owner> <repo> <vouch-app-id> [bypass-user-login-or-id]" >&2
  exit 2
fi

OWNER="$1"
REPO="$2"
APP_ID="$3"
BYPASS_USER="${4:-}"
FULL_REPO="$OWNER/$REPO"
RULESET_NAME="Main Branch"

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI is required" >&2
  exit 1
fi

if ! [[ "$APP_ID" =~ ^[0-9]+$ ]]; then
  echo "error: vouch-app-id must be numeric" >&2
  exit 2
fi

USER_ID=""
if [ -n "$BYPASS_USER" ]; then
  if [[ "$BYPASS_USER" =~ ^[0-9]+$ ]]; then
    USER_ID="$BYPASS_USER"
  else
    USER_ID="$(gh api "users/$BYPASS_USER" --jq '.id')"
  fi
fi

EXISTING_ID="$(
  gh api "repos/$FULL_REPO/rulesets" \
    --jq ".[] | select(.name == \"$RULESET_NAME\" and .target == \"branch\") | .id" \
    | head -n 1
)"

PAYLOAD="$(mktemp)"
trap 'rm -f "$PAYLOAD"' EXIT

python3 - "$APP_ID" "$USER_ID" > "$PAYLOAD" <<'PY'
import json
import sys

app_id = int(sys.argv[1])
user_id = sys.argv[2]

bypass_actors = [
    {
        "actor_id": app_id,
        "actor_type": "Integration",
        "bypass_mode": "always",
    }
]

if user_id:
    bypass_actors.append(
        {
            "actor_id": int(user_id),
            "actor_type": "User",
            "bypass_mode": "always",
        }
    )

payload = {
    "name": "Main Branch",
    "target": "branch",
    "enforcement": "active",
    "bypass_actors": bypass_actors,
    "conditions": {
        "ref_name": {
            "include": ["~DEFAULT_BRANCH"],
            "exclude": [],
        }
    },
    "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "allowed_merge_methods": ["merge", "squash", "rebase"],
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False,
                "require_last_push_approval": True,
                "required_approving_review_count": 1,
                "required_review_thread_resolution": False,
                "required_reviewers": [],
            },
        },
    ],
}

print(json.dumps(payload, indent=2))
PY

if [ -n "$EXISTING_ID" ]; then
  METHOD="PUT"
  ENDPOINT="repos/$FULL_REPO/rulesets/$EXISTING_ID"
else
  METHOD="POST"
  ENDPOINT="repos/$FULL_REPO/rulesets"
fi

gh api "$ENDPOINT" \
  --method "$METHOD" \
  --input "$PAYLOAD" \
  --jq '{id,name,target,enforcement,bypass_actors,rules}'

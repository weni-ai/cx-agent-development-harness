"""PreToolUse hook: make every deploy.py run ask the user for permission.

`deploy.py` publishes the agent to the live Manager of the selected Weni project. In
auto mode the classifier would otherwise deny it outright as a production deploy;
answering "ask" turns that into a normal permission prompt. The skill's own rule (the
user confirms in the chat first) still applies; this only decides how Claude Code asks.

Reads the hook payload on stdin. Prints the "ask" decision for a Bash call that runs
scripts/deploy.py; prints nothing (no opinion) for anything else. Never fails the call.

Usage (from hooks/hooks.json):
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/deploy_permission.py"
"""

from __future__ import annotations

# Standard library
import json
import re
import sys

DEPLOY_COMMAND = re.compile(r"""(^|[\s/"'])scripts/deploy\.py(["'\s]|$)""")
REASON = (
    "Weni deploy: publishes the agent to the live Manager of the selected Weni project "
    "(it runs `weni project push`)."
)


def is_deploy(payload: dict) -> bool:
    if payload.get("tool_name") != "Bash":
        return False
    command = (payload.get("tool_input") or {}).get("command") or ""
    return bool(DEPLOY_COMMAND.search(command))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if isinstance(payload, dict) and is_deploy(payload):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": REASON,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

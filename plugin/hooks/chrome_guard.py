"""PreToolUse hook: keep Claude in Chrome on the Weni agent pages of one project.

In a Weni project, every Claude in Chrome call is denied unless
scripts/platform_session.py opened a session (`.harness/platform_session.json`).
Within it, page tools only act on the session's own tab and navigation is limited
to the project's two agent pages; clicks, typing and plain keys are allowed, while
keyboard shortcuts, JavaScript, form filling, network reads and uploads are denied.
Fails closed.

Limit: a click inside an allowed page has no URL to check; there, the protection is
the weni:platform skill (the user confirms Finish / Remove agent in the chat).
"""

from __future__ import annotations

# Standard library
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PREFIX = "mcp__claude-in-chrome__"
SESSION_FILE = Path(".harness") / "platform_session.json"
OPERATIONS = ("assign", "unassign")
SESSION_TTL = timedelta(minutes=60)
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MY_AGENTS = "https://dash.weni.ai/projects/{uuid}/ai-agents/agents"

ALWAYS_DENY = {"javascript_tool", "form_input", "read_network_requests", "file_upload", "upload_image"}
TAB_FREE = {"tabs_context_mcp", "tabs_create_mcp"}  # needed before the session's tab exists
ALLOWED_ACTIONS = {"screenshot", "zoom", "scroll", "scroll_to", "wait", "hover",
                   "left_click", "double_click", "triple_click", "type", "key"}
RANK = {"allow": 0, "ask": 1, "deny": 2}


def project_dir(payload: dict) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())


def is_weni_project(root: Path) -> bool:
    """Same rule as check_ready.is_harness_project (stdlib only, no venv re-exec)."""
    return (root / ".harness" / "runs").is_dir() or any((root / "agents").glob("*/agent_definition.yaml"))


def load_session(root: Path) -> dict | None:
    """Return the open session, or None when missing, malformed or expired."""
    try:
        session = json.loads((root / SESSION_FILE).read_text(encoding="utf-8"))
        started = datetime.fromisoformat(session["started_at"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if not UUID.match(str(session.get("project_uuid", ""))) or session.get("operation") not in OPERATIONS:
        return None
    if not str(session.get("agent_name", "")).strip():
        return None
    if not timedelta(0) <= datetime.now(timezone.utc) - started <= SESSION_TTL:
        return None
    return session


def is_shortcut(keys: str) -> bool:
    """True for modifier combos and function keys (address bar, history, new tab...)."""
    return any(re.search(r"(^|\+)(cmd|ctrl|alt|meta|win|windows|super|option)\+", part, re.IGNORECASE)
               or re.fullmatch(r"f\d{1,2}", part, re.IGNORECASE) for part in keys.split())


def allowed_urls(session: dict) -> set[str]:
    my_agents = MY_AGENTS.format(uuid=session["project_uuid"])
    return {my_agents, my_agents + "/assign"}


def normalize(url: str) -> str:
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    return url.rstrip("/") if url.count("/") > 3 else url


def check_url(url: str, session: dict) -> tuple[str, str]:
    if url.strip().lower() in ("back", "forward"):
        return "deny", f"Browser history navigation ({url}) is blocked; navigate to an allowed URL instead."
    if normalize(url) in allowed_urls(session):
        return "allow", ""
    allowed = " or ".join(sorted(allowed_urls(session)))
    return "deny", f"Navigation to {url} is blocked. Only {allowed} is allowed."


def decide(name: str, tool_input: dict, session: dict | None) -> tuple[str, str]:
    """Return (decision, reason) for one Chrome tool call."""
    name = name.removeprefix(PREFIX)
    if name in ALWAYS_DENY:
        return "deny", f"{name} is blocked by the Weni harness: the platform is used visually only."
    if session is None:
        return "deny", ("Claude in Chrome is blocked in this Weni project unless weni:platform opened a session "
                        "(scripts/platform_session.py).")
    if name == "browser_batch":
        return decide_batch(tool_input.get("actions") or [], session)
    if "url" in tool_input:
        url_decision = check_url(str(tool_input["url"]), session)
        if url_decision[0] == "deny":
            return url_decision
    if name in TAB_FREE:
        return "allow", ""
    tab = session.get("tab_id")
    if tab is None or tool_input.get("tabId") != tab:
        return "deny", (f"{name} may only act on the session's tab ({tab}); bind it with "
                        "platform_session.py --bind-tab <id> after tabs_create_mcp.")
    if name == "navigate":
        return check_url(str(tool_input.get("url", "")), session)
    if name == "computer":
        action = tool_input.get("action", "")
        if action == "key" and is_shortcut(str(tool_input.get("text", ""))):
            return "deny", f"Keyboard shortcut {tool_input.get('text')!r} is blocked by the Weni harness."
        if action in ALLOWED_ACTIONS:
            return "allow", ""
        return "deny", f"computer action {action!r} is not allowed by the Weni harness."
    if name in ("find", "tabs_close_mcp"):
        return "allow", ""
    if name == "read_page":
        if tool_input.get("ref_id") or tool_input.get("filter") == "interactive":
            return "allow", ""
        return "deny", "read_page on the whole page is blocked; pass ref_id or filter: interactive (or use find)."
    return "deny", f"{name} is not allowed by the Weni harness."


def decide_batch(actions: list, session: dict) -> tuple[str, str]:
    results = []
    for index, item in enumerate(actions, 1):
        item = item if isinstance(item, dict) else {}
        name = str(item.get("name", "")).removeprefix(PREFIX)
        tool_input = item.get("input") if isinstance(item.get("input"), dict) else {}
        if name == "browser_batch":
            results.append(("deny", f"{index}. nested browser_batch is not allowed"))
            continue
        decision, reason = decide(name, tool_input, session)
        label = f"{name} {tool_input.get('action', '')}".strip()
        results.append((decision, f"{index}. {label}" + (f": {reason}" if reason else "")))
    if not results:
        return "deny", "Empty browser_batch."
    worst = max((decision for decision, _ in results), key=RANK.__getitem__)
    if worst == "allow":
        return "allow", ""
    shown = [line for decision, line in results if decision == "deny"] if worst == "deny" else [line for _, line in results]
    head = "Batch blocked:" if worst == "deny" else "Weni platform batch:"
    return worst, head + " " + "; ".join(shown)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = None
    root = project_dir(payload if isinstance(payload, dict) else {})
    if not is_weni_project(root):
        return 0
    try:
        tool_name = str(payload["tool_name"])
        tool_input = payload.get("tool_input")
        if not tool_name.startswith(PREFIX) or not isinstance(tool_input, dict):
            raise ValueError("unexpected payload")
        decision, reason = decide(tool_name, tool_input, load_session(root))
    except Exception:  # fail closed: the matcher only sends Chrome calls here
        decision, reason = "deny", "Malformed Claude in Chrome call; blocked by the Weni harness."
    output = {"hookEventName": "PreToolUse", "permissionDecision": decision}
    if reason:
        output["permissionDecisionReason"] = reason
    print(json.dumps({"hookSpecificOutput": output}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

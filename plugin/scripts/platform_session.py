"""Open or close the browser session that lets weni:platform drive Chrome.

The Chrome guard hook (hooks/chrome_guard.py) denies every Claude in Chrome call
in a Weni project unless `.harness/platform_session.json` exists, and then only
allows navigating to the two agent pages of the project recorded there. This
script is the only writer of that file:

- the project is `weni project current` (the same one `weni eval` uses);
- the agent name is `name` from agents/<slug>/agent_definition.yaml: the platform
  shows the agent by that name, never by slug.

Opening replaces any previous session. Until `--bind-tab` records the tab created
with tabs_create_mcp, the guard only allows tabs_context_mcp/tabs_create_mcp; after
that, page tools only act on that tab.

Prints PLATFORM_SESSION_OPEN (agent name and allowed URLs), PLATFORM_TAB_BOUND, or
PLATFORM_SESSION_CLOSED.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/platform_session.py" --target <slug> --operation assign|unassign
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/platform_session.py" --bind-tab <tabId>
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/platform_session.py" --close
"""

from __future__ import annotations

# Standard library
import argparse
import json
import re
from datetime import datetime, timezone

# Local
from _common import platform_session_path
from check_ready import current_project, ensure_ready
from platform_preflight import load_agent

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
MY_AGENTS = "https://dash.weni.ai/projects/{uuid}/ai-agents/agents"


def main() -> None:
    parser = argparse.ArgumentParser(description="Open or close the weni:platform browser session.")
    parser.add_argument("--target", help="Collaborator slug (agents/<slug>/).")
    parser.add_argument("--operation", choices=("assign", "unassign"))
    parser.add_argument("--bind-tab", type=int, metavar="TAB_ID", help="Restrict the open session to this tab.")
    parser.add_argument("--close", action="store_true", help="Close the session (Chrome is denied again).")
    args = parser.parse_args()

    path = platform_session_path()
    if args.bind_tab is not None:
        if not path.exists():
            raise SystemExit("No open session: open one with --target and --operation first.")
        session = json.loads(path.read_text(encoding="utf-8"))
        if "tab_id" in session:
            raise SystemExit(f"The session is already bound to tab {session['tab_id']}; open a new session.")
        session["tab_id"] = args.bind_tab
        path.write_text(json.dumps(session, indent=2), encoding="utf-8")
        print("PLATFORM_TAB_BOUND")
        return
    path.unlink(missing_ok=True)  # a failed open must not leave an older session usable
    if args.close:
        print("PLATFORM_SESSION_CLOSED")
        return
    if not args.operation:
        parser.error("--operation is required unless --close or --bind-tab")

    ensure_ready()
    project = current_project()
    if not UUID.match(project):
        raise SystemExit(f"The selected Weni project is not a UUID: {project!r}")
    name = (load_agent(args.target).get("name") or "").strip()
    if not name:
        raise SystemExit("The agent has no `name` in agent_definition.yaml.")

    session = {
        "project_uuid": project.lower(),
        "agent_name": name,
        "operation": args.operation,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2), encoding="utf-8")

    my_agents = MY_AGENTS.format(uuid=session["project_uuid"])
    print("PLATFORM_SESSION_OPEN")
    print(f"Operation: {args.operation}")
    print(f"Agent name (exact match): {name}")
    print(f"My agents: {my_agents}")
    print(f"Assign new agents: {my_agents}/assign")


if __name__ == "__main__":
    main()

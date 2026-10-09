"""Decide whether the browser may assign a collaborator, before it is deployed.

Assigning on the Weni platform opens a setup form with the agent's credentials and
constants. The harness never types values there, so the browser can only finish the
assignment when every field already has a value:

- confidential credentials (`is_confidential: true`, or the field missing: the
  default is true) are never pre-filled;
- non-confidential credentials and constants are pre-filled only from `default`.

Prints ASSIGN_AUTO (nothing to fill in) or ASSIGN_MANUAL followed by one line per
field label the user has to fill in on the platform.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/platform_preflight.py" --target <slug>
"""

from __future__ import annotations

# Standard library
import argparse
import sys

# Local
from _common import agent_dir

# Third-party
try:
    import yaml
except ImportError:
    print("PyYAML is required. Run this script with the project .venv python.", file=sys.stderr)
    raise SystemExit(2)


def load_agent(slug: str | None) -> dict:
    """Return the single agent block of agents/<slug>/agent_definition.yaml."""
    path = agent_dir(slug) / "agent_definition.yaml"
    if not path.exists():
        raise SystemExit(f"Not found: {path}")
    definition = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    agents = definition.get("agents") or {}
    if len(agents) != 1:
        raise SystemExit(f"{path} must define exactly one agent (found {len(agents)}).")
    return next(iter(agents.values())) or {}


def has_default(field: dict) -> bool:
    return field.get("default") not in (None, "")


def fields_to_fill(agent: dict) -> list[str]:
    """Return the labels of the setup fields the browser cannot complete."""
    missing = []
    for key, field in (agent.get("credentials") or {}).items():
        field = field or {}
        confidential = field.get("is_confidential", True) is not False
        if confidential or not has_default(field):
            label = field.get("label") or key
            missing.append(f"{label} (confidential credential)" if confidential else label)
    for key, field in (agent.get("constants") or {}).items():
        field = field or {}
        if not has_default(field):
            missing.append(field.get("label") or key)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether the browser can assign a collaborator.")
    parser.add_argument("--target", help="Collaborator slug (agents/<slug>/).")
    args = parser.parse_args()

    missing = fields_to_fill(load_agent(args.target))
    if not missing:
        print("ASSIGN_AUTO")
        return
    print("ASSIGN_MANUAL")
    for label in missing:
        print(f"- {label}")


if __name__ == "__main__":
    main()

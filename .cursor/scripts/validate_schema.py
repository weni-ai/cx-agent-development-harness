"""Validate an agent_definition.yaml against the Weni constitution constraints.

This is a deterministic, token-free gate that runs after the implementer and
before the tester. It enforces the hard limits the Weni CLI would otherwise
reject at deploy time, plus the harness rule that only TextResponse and
FinalResponse may be used.

Exit codes:
    0  valid
    1  validation errors found
    2  could not run (missing file or dependency)
"""

# Standard library
import argparse
import re
import sys
from pathlib import Path

# Third-party
try:
    import yaml
except ImportError:
    print("PyYAML is required. Run this script with the project .venv python.", file=sys.stderr)
    raise SystemExit(2)

# Local
from _common import agent_dir

LEGACY_RESPONSES = (
    "AttachmentResponse",
    "QuickReplyResponse",
    "ListMessageResponse",
    "CTAMessageResponse",
    "OrderDetailsResponse",
    "LocationResponse",
)
CONTACT_FIELD_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
REQUIRED_TOOL_FILES = ("main.py", "requirements.txt", "test_definition.yaml")


def add_error(errors: list, message: str) -> None:
    """Record a validation error message."""
    errors.append(message)


def validate_tool(tool_key: str, tool: dict, root: Path, errors: list) -> None:
    """Validate a single tool definition and its on-disk folder."""
    name = tool.get("name", "")
    description = tool.get("description", "")
    source = tool.get("source", {}) or {}

    if len(name) > 40:
        add_error(errors, f"tool '{tool_key}': name exceeds 40 chars ({len(name)})")
    if not description:
        add_error(errors, f"tool '{tool_key}': description is required")
    if len(description) > 200:
        add_error(errors, f"tool '{tool_key}': description exceeds 200 chars ({len(description)})")
    if not source.get("path"):
        add_error(errors, f"tool '{tool_key}': source.path is required")
    if not source.get("entrypoint"):
        add_error(errors, f"tool '{tool_key}': source.entrypoint is required")

    tool_path = root / source.get("path", "")
    if source.get("path") and not tool_path.exists():
        add_error(errors, f"tool '{tool_key}': folder '{source['path']}' does not exist")
        return

    if source.get("path"):
        for required in REQUIRED_TOOL_FILES:
            if not (tool_path / required).exists():
                add_error(errors, f"tool '{tool_key}': missing required file '{required}'")
        main_file = tool_path / "main.py"
        if main_file.exists():
            code = main_file.read_text(encoding="utf-8")
            for legacy in LEGACY_RESPONSES:
                if legacy in code:
                    add_error(errors, f"tool '{tool_key}': uses forbidden legacy response '{legacy}'")

    for param in tool.get("parameters", []) or []:
        for param_name, param_def in param.items():
            if (param_def or {}).get("contact_field"):
                if not CONTACT_FIELD_PATTERN.match(param_name):
                    add_error(errors, f"tool '{tool_key}': contact field '{param_name}' breaks naming pattern")
                if len(param_name) > 36:
                    add_error(errors, f"tool '{tool_key}': contact field '{param_name}' exceeds 36 chars")


def validate_agent(agent_key: str, agent: dict, root: Path, errors: list) -> None:
    """Validate a single agent definition."""
    name = agent.get("name", "")
    if not name:
        add_error(errors, f"agent '{agent_key}': name is required")
    if len(name) > 55:
        add_error(errors, f"agent '{agent_key}': name exceeds 55 chars ({len(name)})")
    if not agent.get("description"):
        add_error(errors, f"agent '{agent_key}': description is required")

    for instruction in agent.get("instructions", []) or []:
        if len(instruction) < 40:
            add_error(errors, f"agent '{agent_key}': instruction under 40 chars: '{instruction[:30]}...'")
    for guardrail in agent.get("guardrails", []) or []:
        if len(guardrail) < 40:
            add_error(errors, f"agent '{agent_key}': guardrail under 40 chars: '{guardrail[:30]}...'")

    tools = agent.get("tools", []) or []
    if not tools:
        add_error(errors, f"agent '{agent_key}': at least one tool is required")
    for tool_entry in tools:
        for tool_key, tool in tool_entry.items():
            validate_tool(tool_key, tool, root, errors)


def main() -> None:
    """Parse arguments, validate the definition, and report the result."""
    parser = argparse.ArgumentParser(description="Validate agent_definition.yaml.")
    parser.add_argument("--file", default="agent_definition.yaml", help="Definition file path.")
    parser.add_argument(
        "--target",
        help="Collaborator slug to validate (folder agents/<slug>/). "
        "Optional when the project has a single agent.",
    )
    args = parser.parse_args()

    root = agent_dir(args.target)
    definition_path = (root / args.file) if not Path(args.file).is_absolute() else Path(args.file)
    if not definition_path.exists():
        print(f"Definition file not found: {definition_path}", file=sys.stderr)
        raise SystemExit(2)

    with open(definition_path, "r", encoding="utf-8") as definition_file:
        definition = yaml.safe_load(definition_file) or {}

    errors: list = []
    agents = definition.get("agents", {}) or {}
    if not agents:
        add_error(errors, "no agents defined under top-level 'agents'")
    for agent_key, agent in agents.items():
        validate_agent(agent_key, agent, root, errors)

    if errors:
        print(f"SCHEMA_INVALID ({len(errors)} error(s)):")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)

    print("SCHEMA_VALID")


if __name__ == "__main__":
    main()

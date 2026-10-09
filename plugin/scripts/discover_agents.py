"""Find every Weni collaborator agent in the project, wherever it lives.

An agent is a folder with an `agent_definition.yaml` whose top-level `agents` mapping
is not empty and whose tool `source.path` folders exist inside that folder. The
harness expects each one at `agents/<slug>/`; anything else is reported so it can be
moved there with adopt_agent.py. Read-only.

Output: one line per agent, then a summary line.
    IN_PLACE  <slug>  agents/<slug>
    LOOSE     <slug>  <path>  -> agents/<slug>
    INVALID   -       <path>  <reason>
    AGENTS_IN_PLACE | LOOSE_AGENTS_FOUND <n> | NO_AGENTS_FOUND

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/discover_agents.py [--json]
"""

from __future__ import annotations

# Standard library
import argparse
import json
import re
from pathlib import Path

# Local (first: _common re-runs this script inside the project .venv, which has PyYAML)
from _common import agents_root, project_root

# Third-party
try:
    import yaml
except ImportError:  # Not set up yet: agents are still found, just not verified.
    yaml = None

DEFINITION = "agent_definition.yaml"
MAX_DEPTH = 4
SKIP_DIRS = {"node_modules", "venv", "env", "__pycache__", "site-packages", "dist", "build"}
# Root-level files that belong to the agent when the definition sits at the project root.
ROOT_AGENT_FILES = (DEFINITION, "agent_evaluation.yml")


def to_slug(text: str) -> str:
    """Turn a folder name or agent key into a kebab-case slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def find_definitions(root: Path) -> list[Path]:
    """Return every agent folder (the parent of a definition), not descending into agents."""
    found: list[Path] = []

    def walk(folder: Path, depth: int) -> None:
        if (folder / DEFINITION).is_file():
            found.append(folder)
            if folder != root:
                return
        if depth >= MAX_DEPTH:
            return
        try:
            children = sorted(folder.iterdir())
        except OSError:  # Unreadable folder: skip it, discovery never fails.
            return
        for child in children:
            if child.is_dir() and not child.is_symlink() and not child.name.startswith(".") and child.name not in SKIP_DIRS:
                walk(child, depth + 1)

    walk(root, 0)
    return found


def check_definition(folder: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (agent keys, top-level tool folders, problems) for a definition."""
    if yaml is None:
        return [], [], []
    try:
        definition = yaml.safe_load((folder / DEFINITION).read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, UnicodeDecodeError) as error:
        return [], [], [f"{DEFINITION} is not valid YAML ({str(error).splitlines()[0]})"]
    agents = definition.get("agents") if isinstance(definition, dict) else None
    if not isinstance(agents, dict) or not agents:
        return [], [], [f"{DEFINITION} has no agents under top-level 'agents'"]

    tool_dirs: list[str] = []
    problems: list[str] = []
    for agent in agents.values():
        for entry in (agent or {}).get("tools", []) or []:
            for tool_key, tool in (entry or {}).items():
                path = ((tool or {}).get("source") or {}).get("path")
                if not path:
                    continue
                resolved = (folder / path).resolve()
                if not resolved.is_relative_to(folder.resolve()):
                    problems.append(f"tool '{tool_key}': source.path '{path}' is outside the agent folder")
                elif not resolved.is_dir():
                    problems.append(f"tool '{tool_key}': source.path '{path}' does not exist")
                else:
                    top = Path(path).parts[0]
                    if top not in tool_dirs:
                        tool_dirs.append(top)
    return list(agents), tool_dirs, problems


def discover() -> list[dict]:
    """Classify every agent folder in the project as IN_PLACE, LOOSE or INVALID."""
    root = project_root()
    home = agents_root()
    results: list[dict] = []
    for folder in find_definitions(root):
        keys, tool_dirs, problems = check_definition(folder)
        relative = "." if folder == root else folder.relative_to(root).as_posix()
        if problems:
            results.append({"status": "INVALID", "slug": None, "path": relative, "reason": "; ".join(problems)})
            continue
        in_place = folder.parent == home
        if in_place:
            slug = folder.name
        elif folder == root:
            slug = to_slug(keys[0]) if keys else to_slug(root.name)
        else:
            slug = to_slug(folder.name)
        result = {
            "status": "IN_PLACE" if in_place else "LOOSE",
            "slug": slug,
            "path": relative,
            "agents": keys,
            "verified": yaml is not None,
        }
        if folder == root:
            # Only the agent's own files move out of the root; the rest stays.
            result["moves"] = [name for name in ROOT_AGENT_FILES if (root / name).exists()] + tool_dirs
        if len(keys) > 1:
            result["warning"] = f"defines {len(keys)} agents; the harness expects one per folder"
        results.append(result)
    return results


def main() -> None:
    """Print the discovered agents and a summary line."""
    parser = argparse.ArgumentParser(description="Find Weni agents in this project.")
    parser.add_argument("--json", action="store_true", help="Print the result as JSON.")
    args = parser.parse_args()

    results = discover()
    if args.json:
        print(json.dumps(results, indent=2))
        return
    for item in results:
        if item["status"] == "INVALID":
            print(f"INVALID   -  {item['path']}  {item['reason']}")
            continue
        line = f"{item['status']:<9} {item['slug']}  {item['path']}"
        if item["status"] == "LOOSE":
            line += f"  -> agents/{item['slug']}"
        if item.get("warning"):
            line += f"  (warning: {item['warning']})"
        if not item["verified"]:
            line += "  (not verified: PyYAML missing until setup)"
        print(line)
    loose = sum(1 for item in results if item["status"] == "LOOSE")
    if loose:
        print(f"LOOSE_AGENTS_FOUND {loose}")
    elif any(item["status"] == "IN_PLACE" for item in results):
        print("AGENTS_IN_PLACE")
    else:
        print("NO_AGENTS_FOUND")


if __name__ == "__main__":
    main()

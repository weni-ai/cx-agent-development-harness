"""Move agents found outside `agents/` into `agents/<slug>/`, where the harness works.

Uses discover_agents.py to find LOOSE agents. A subfolder agent moves whole (tools,
eval, README, local .env/.globals and any extra files). An agent defined at the
project root moves only its own files (definition, eval, tool folders); the rest of
the root stays. Tool `source.path` values are relative, so they keep working. Never
overwrites an existing `agents/<slug>/` and never moves an INVALID agent. Git sees
the moves as renames when they are committed.

Run with --dry-run first, show the plan to the user, and move only after they confirm.

Output: one line per agent, then a summary line.
    ADOPT     <path> -> agents/<slug>          (--dry-run)
    ADOPTED   <path> -> agents/<slug>
    SKIPPED   <path>  <reason>
    ADOPT_DONE | ADOPT_PARTIAL | NOTHING_TO_ADOPT

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/adopt_agent.py --all --dry-run
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/adopt_agent.py --all
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/adopt_agent.py --from legacy/order_bot --slug order-bot
"""

from __future__ import annotations

# Standard library
import argparse
import shutil
from pathlib import Path

# Local (first: _common re-runs this script inside the project .venv, which has PyYAML)
from _common import agents_root, project_root
from discover_agents import discover, to_slug


def plan(items: list[dict], slug_override: str | None) -> list[tuple[dict, str | None, str | None]]:
    """Pair each agent with its destination slug or the reason it cannot move."""
    taken = {path.name for path in agents_root().iterdir()} if agents_root().exists() else set()
    planned = []
    for item in items:
        if item["status"] == "INVALID":
            planned.append((item, None, item["reason"]))
            continue
        if item["status"] == "IN_PLACE":
            planned.append((item, None, "already in agents/"))
            continue
        slug = to_slug(slug_override) if slug_override else item["slug"]
        if not slug:
            planned.append((item, None, "no usable slug; pass --from <path> --slug <slug>"))
        elif slug in taken:
            planned.append((item, None, f"agents/{slug} already exists; pass --from <path> --slug <other>"))
        else:
            taken.add(slug)
            planned.append((item, slug, None))
    return planned


def move(item: dict, slug: str) -> None:
    """Move one agent into agents/<slug>/."""
    root = project_root()
    destination = agents_root() / slug
    if item["path"] == ".":
        destination.mkdir(parents=True)
        for name in item["moves"]:
            shutil.move(str(root / name), str(destination / name))
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root / item["path"]), str(destination))


def main() -> None:
    """Parse arguments, then plan or perform the moves."""
    parser = argparse.ArgumentParser(description="Move agents into agents/<slug>/.")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--all", action="store_true", help="Adopt every LOOSE agent.")
    which.add_argument("--from", dest="source", help="Adopt the agent in this folder ('.' for the project root).")
    parser.add_argument("--slug", help="Destination slug (only with --from).")
    parser.add_argument("--dry-run", action="store_true", help="Show what would move; change nothing.")
    args = parser.parse_args()
    if args.slug and not args.source:
        parser.error("--slug only works with --from")

    found = discover()
    if args.source:
        root = project_root()
        wanted = (root / args.source).resolve()
        items = [item for item in found if (root / item["path"]).resolve() == wanted]
        if not items:
            print(f"NOT_AN_AGENT {args.source}: no agent_definition.yaml found there")
            raise SystemExit(1)
    else:
        items = [item for item in found if item["status"] != "IN_PLACE"]
    if not items:
        print("NOTHING_TO_ADOPT")
        return

    skipped = 0
    for item, slug, reason in plan(items, args.slug):
        if reason:
            skipped += 1
            print(f"SKIPPED   {item['path']}  {reason}")
            continue
        detail = f"  (moves only: {', '.join(item['moves'])})" if item["path"] == "." else ""
        if args.dry_run:
            print(f"ADOPT     {item['path']} -> agents/{slug}{detail}")
            continue
        move(item, slug)
        print(f"ADOPTED   {item['path']} -> agents/{slug}{detail}")

    if args.dry_run:
        return
    print("ADOPT_PARTIAL" if skipped else "ADOPT_DONE")
    raise SystemExit(1 if skipped else 0)


if __name__ == "__main__":
    main()

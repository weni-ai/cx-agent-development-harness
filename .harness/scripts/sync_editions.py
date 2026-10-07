"""Generate the Cursor edition files from the Claude Code ones.

`.claude/` is the single source for subagent briefs and slash commands. Cursor
already reads `.claude/skills/` (and `AGENTS.md`), so only two things need a
Cursor-specific copy:

- `.cursor/agents/*.md`: same body, frontmatter translated (model id, readonly).
- `.cursor/commands/*.md`: same prompt, without Claude frontmatter.

Edit the `.claude/` file, then run `./harness sync`. `--check` fails if the
Cursor copies are stale (used by the harness tests).

Usage:
    python3 .harness/scripts/sync_editions.py
    python3 .harness/scripts/sync_editions.py --check
"""

from __future__ import annotations

# Standard library
import argparse
from pathlib import Path

# Local
from _common import project_root

# Claude model alias -> Cursor model id. Claude aliases always resolve to the latest
# model of that tier; Cursor needs explicit ids, so update them here when Cursor ships
# newer ones. Cost intent: strongest for planning, capable mid model for
# build/test/review, cheap model for docs.
CURSOR_MODELS = {
    "opus": "claude-opus-5.5",
    "sonnet": "composer-2.5[fast=false]",
    "haiku": "gemini-3.8-flash",
}

# Subagents that must not modify the project (Cursor `readonly: true`; in Claude
# Code the same restriction comes from the `tools:` allowlist).
READONLY_AGENTS = {"reviewer"}

GENERATED_NOTE = "<!-- Generated from .claude/{kind}/{name} by `./harness sync`. Edit the source, not this file. -->"


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a markdown file into (flat frontmatter dict, body)."""
    if not text.startswith("---\n"):
        return {}, text
    header, body = text[4:].split("\n---\n", 1)
    fields = {}
    for line in header.splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, body.lstrip("\n")


def cursor_agent(source: Path) -> str:
    """Translate one Claude subagent brief into its Cursor form."""
    fields, body = split_frontmatter(source.read_text(encoding="utf-8"))
    model = fields.get("model", "inherit")
    lines = [
        "---",
        f"name: {fields['name']}",
        f"description: {fields['description']}",
        f"model: {CURSOR_MODELS.get(model, model)}",
    ]
    if fields["name"] in READONLY_AGENTS:
        lines.append("readonly: true")
    lines += ["---", "", GENERATED_NOTE.format(kind="agents", name=source.name), "", body]
    return "\n".join(lines)


def cursor_command(source: Path) -> str:
    """Translate one Claude slash command into a Cursor command."""
    _, body = split_frontmatter(source.read_text(encoding="utf-8"))
    body = body.replace("$ARGUMENTS", "the text the user typed after the command")
    return GENERATED_NOTE.format(kind="commands", name=source.name) + "\n\n" + body


def planned_files() -> dict[Path, str]:
    """Return every Cursor file this script owns, mapped to its expected content."""
    root = project_root()
    files = {}
    for source in sorted((root / ".claude" / "agents").glob("*.md")):
        files[root / ".cursor" / "agents" / source.name] = cursor_agent(source)
    for source in sorted((root / ".claude" / "commands").glob("*.md")):
        files[root / ".cursor" / "commands" / source.name] = cursor_command(source)
    return files


def main() -> None:
    """Write the Cursor files, or verify they are current with --check."""
    parser = argparse.ArgumentParser(description="Generate Cursor edition files from .claude/.")
    parser.add_argument("--check", action="store_true", help="Fail if Cursor files are stale.")
    args = parser.parse_args()

    root = project_root()
    files = planned_files()
    owned_dirs = (root / ".cursor" / "agents", root / ".cursor" / "commands")
    orphans = [
        path for folder in owned_dirs if folder.exists() for path in folder.glob("*.md") if path not in files
    ]
    stale = [path for path, content in files.items() if not path.exists() or path.read_text(encoding="utf-8") != content]

    if args.check:
        problems = stale + orphans
        for path in problems:
            print(f"STALE {path.relative_to(root)}")
        print("SYNC_STALE (run ./harness sync)" if problems else "SYNC_OK")
        raise SystemExit(1 if problems else 0)

    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[path], encoding="utf-8")
        print(f"wrote   {path.relative_to(root)}")
    for path in orphans:
        path.unlink()
        print(f"removed {path.relative_to(root)}")
    print("SYNC_OK")


if __name__ == "__main__":
    main()

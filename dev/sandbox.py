"""Disposable partner-like projects for testing plugin changes end to end.

    dev/harness sandbox new <scenario>        empty git project, prints how to open it
    dev/harness sandbox list                  show sandboxes with age and size
    dev/harness sandbox clean [--older-than DAYS]

A sandbox is an empty folder (like a partner's new project) opened with
`claude --plugin-dir <repo>/plugin`, so it always runs your working copy of the
plugin. Sandboxes live only under ~/.harness-sandboxes/ (override:
HARNESS_SANDBOX_ROOT) and carry a `.harness-sandbox` marker; `clean` deletes
nothing without it. The repo's .venv is symlinked and the Weni login lives in
~/.weni_cli, so a new sandbox needs no reinstall and no new login.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "dev" / "scenarios"
SANDBOX_ROOT = Path(os.environ.get("HARNESS_SANDBOX_ROOT", Path.home() / ".harness-sandboxes"))
MARKER = ".harness-sandbox"
WARN_ABOVE = 3
def sandboxes():
    """Return every marked sandbox directory, oldest first."""
    if not SANDBOX_ROOT.exists():
        return []
    return sorted(path for path in SANDBOX_ROOT.iterdir() if (path / MARKER).exists())


def cmd_new(args):
    scenario = SCENARIOS / f"{args.scenario}.md"
    if not scenario.exists():
        available = ", ".join(sorted(path.stem for path in SCENARIOS.glob("*.md")))
        print(f"Unknown scenario '{args.scenario}'. Available: {available}")
        return 2
    base = f"{datetime.now():%Y%m%d-%H%M%S}-{args.scenario}"
    dest, suffix = SANDBOX_ROOT / base, 2
    while dest.exists():  # two sandboxes in the same second
        dest, suffix = SANDBOX_ROOT / f"{base}-{suffix}", suffix + 1
    dest.mkdir(parents=True)
    (dest / MARKER).write_text(f"source={ROOT}\nscenario={args.scenario}\n", encoding="utf-8")
    if (ROOT / ".venv").exists():
        (dest / ".venv").symlink_to(ROOT / ".venv", target_is_directory=True)
    (dest / ".gitignore").write_text(f"{MARKER}\n", encoding="utf-8")
    subprocess.call(["git", "init", "-q"], cwd=str(dest))

    print(f"Sandbox ready: {dest}\n")
    print(scenario.read_text(encoding="utf-8"))
    print(f"Open it:   cd {dest} && claude --plugin-dir {ROOT / 'plugin'}")
    print("When done: describe what failed in the harness repo session, then `dev/harness sandbox clean`.")
    if len(sandboxes()) > WARN_ABOVE:
        print(f"\nNote: {len(sandboxes())} sandboxes exist. Run `dev/harness sandbox clean`.")
    return 0


def size_mb(path):
    total = 0
    for folder, _, files in os.walk(path):  # does not follow the .venv symlink
        total += sum((Path(folder) / name).lstat().st_size for name in files)
    return total / 1_000_000


def cmd_list(_args):
    found = sandboxes()
    if not found:
        print(f"No sandboxes in {SANDBOX_ROOT}")
    for path in found:
        age_days = (time.time() - path.stat().st_mtime) / 86400
        print(f"{path.name:<45} {age_days:5.1f} days  {size_mb(path):7.1f} MB")
    return 0


def cmd_clean(args):
    removed = 0
    for path in sandboxes():
        age_days = (time.time() - path.stat().st_mtime) / 86400
        if args.older_than is not None and age_days < args.older_than:
            continue
        shutil.rmtree(path)
        print(f"removed {path}")
        removed += 1
    print(f"{removed} sandbox(es) removed.")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="dev/harness sandbox", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="Create a sandbox for a scenario")
    new.add_argument("scenario", help="Scenario name from dev/scenarios/")
    sub.add_parser("list", help="List sandboxes")
    clean = sub.add_parser("clean", help="Delete sandboxes (only marked ones)")
    clean.add_argument("--older-than", type=float, metavar="DAYS", help="Only those older than DAYS")
    args = parser.parse_args()
    return {"new": cmd_new, "list": cmd_list, "clean": cmd_clean}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

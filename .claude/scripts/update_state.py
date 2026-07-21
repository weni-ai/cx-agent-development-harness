"""Update the live run state snapshot.

Mutates STATE.json and rewrites STATE.md as a whole. Only the orchestrator (the
main session) should call this script. It is deterministic and consumes no LLM
tokens.

Usage:
    python .claude/scripts/update_state.py --run-dir <dir> --phase plan --status in-progress
    python .claude/scripts/update_state.py --latest --phase plan --status done --artifact 02-plan.md
    python .claude/scripts/update_state.py --latest --focus "Waiting for reviewer" --checkpoint "Tests passed"
"""

# Standard library
import argparse
from pathlib import Path

# Local
from _common import (
    VALID_STATUSES,
    find_phase,
    latest_open_run,
    load_state,
    save_state,
)


def resolve_run_dir(args: argparse.Namespace) -> Path:
    """Resolve the target run directory from explicit path or --latest."""
    if args.run_dir:
        return Path(args.run_dir)
    run_dir = latest_open_run()
    if run_dir is None:
        raise SystemExit("No open run found. Pass --run-dir explicitly.")
    return run_dir


def main() -> None:
    """Parse arguments and apply the requested state mutations."""
    parser = argparse.ArgumentParser(description="Update the live run state.")
    parser.add_argument("--run-dir", help="Target run directory.")
    parser.add_argument("--latest", action="store_true", help="Use the latest open run.")
    parser.add_argument("--phase", help="Phase selector (num like '02' or key like 'plan').")
    parser.add_argument("--status", choices=VALID_STATUSES, help="New status for the phase.")
    parser.add_argument("--artifact", help="Artifact filename to record on the phase.")
    parser.add_argument("--checkpoint", help="Latest checkpoint label.")
    parser.add_argument("--focus", help="Current focus text.")
    parser.add_argument("--resume-hint", help="Resume hint text.")
    parser.add_argument("--add-blocker", action="append", default=[], help="Append an open blocker.")
    parser.add_argument("--clear-blockers", action="store_true", help="Clear all blockers.")
    args = parser.parse_args()

    run_dir = resolve_run_dir(args)
    state = load_state(run_dir)

    if args.phase:
        phase = find_phase(state, args.phase)
        if args.status:
            phase["status"] = args.status
        if args.artifact:
            phase["artifact"] = args.artifact
    elif args.status or args.artifact:
        parser.error("--status/--artifact require --phase")

    if args.checkpoint is not None:
        state["checkpoint"] = args.checkpoint
    if args.focus is not None:
        state["focus"] = args.focus
    if args.resume_hint is not None:
        state["resume_hint"] = args.resume_hint
    if args.clear_blockers:
        state["blockers"] = []
    if args.add_blocker:
        state.setdefault("blockers", []).extend(args.add_blocker)

    save_state(run_dir, state)
    print(f"Updated {run_dir}")


if __name__ == "__main__":
    main()

"""Record whether a collaborator is assigned to the Manager of the selected project.

`weni eval` only reaches a collaborator that is assigned to the project's Manager,
and the Weni CLI cannot assign: it is done on the platform (weni:platform, or the
user by hand). The orchestrator runs this after each verified assignment change, so
run_eval.py can refuse with EVAL_NOT_ASSIGNED. The record lives next to the
deployment in `.harness/deployments.json` and is tied to the project selected now;
recording twice overwrites, it never duplicates.

`--by`: `harness` (the browser did it in this run), `user` (the user did it by hand),
`preexisting` (it was already assigned before this run; never offer to unassign it).

Prints ASSIGNMENT_RECORDED.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record_assignment.py" --target <slug> \\
        --status assigned|unassigned --by harness|user|preexisting [--run-dir <RUN_DIR>]
"""

from __future__ import annotations

# Standard library
import argparse
from pathlib import Path

# Local
from _common import ASSIGNMENT_SOURCES, ASSIGNMENT_STATUSES, latest_open_run, load_state, record_assignment
from check_ready import current_project, ensure_ready


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a collaborator's Manager assignment.")
    parser.add_argument("--target", required=True, help="Collaborator slug (agents/<slug>/).")
    parser.add_argument("--status", required=True, choices=ASSIGNMENT_STATUSES)
    parser.add_argument("--by", required=True, choices=ASSIGNMENT_SOURCES)
    parser.add_argument("--run-dir", help="Run that made (or found) the change (default: the latest open run).")
    args = parser.parse_args()

    ensure_ready()
    project = current_project()
    if not project:
        raise SystemExit("No Weni project selected (`weni project use <uuid>`).")
    run_dir = Path(args.run_dir) if args.run_dir else latest_open_run(args.target)
    run_id = load_state(run_dir).get("run_id", run_dir.name) if run_dir else "none"

    assignment = record_assignment(args.target, project, args.status, args.by, run_id)
    print("ASSIGNMENT_RECORDED")
    print(f"{args.target}: {assignment['status']} by {assignment['by']} in project {project} (run {run_id})")


if __name__ == "__main__":
    main()

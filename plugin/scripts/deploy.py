"""Push one collaborator to the selected Weni project and record what was pushed.

Deploying publishes the agent to that project's live Manager, so the orchestrator
runs this ONLY after the user confirmed it in the same turn. The record
(`.harness/deployments.json`: project + fingerprint of the deployable files) is what
lets run_eval.py refuse to evaluate an agent that is not deployed or is stale.

`--record-only` records without pushing, for when the user states the current
local version is already deployed (pushed outside the harness).

Prints DEPLOY_OK or DEPLOY_FAIL.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/deploy.py" --target <slug>
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/deploy.py" --target <slug> --record-only
"""

from __future__ import annotations

# Standard library
import argparse
import subprocess

# Local
from _common import agent_dir, record_deployment, venv_bin
from check_ready import current_project, ensure_ready

PUSH_TIMEOUT_SECONDS = 600
FAILURE_MARKERS = ("Traceback (most recent call last)",)


def main() -> None:
    """Push (or just record) the collaborator and persist the deployment record."""
    parser = argparse.ArgumentParser(description="Push a collaborator and record the deployment.")
    parser.add_argument("--target", required=True, help="Collaborator slug (agents/<slug>/).")
    parser.add_argument("--record-only", action="store_true", help="Record without pushing.")
    args = parser.parse_args()

    ensure_ready()
    project = current_project()
    if not project:
        print("DEPLOY_FAIL")
        print("No Weni project selected (`weni project use <uuid>`).")
        raise SystemExit(1)

    if not args.record_only:
        try:
            result = subprocess.run(
                [str(venv_bin("weni")), "project", "push", "agent_definition.yaml"],
                cwd=str(agent_dir(args.target)),
                input="",
                capture_output=True,
                text=True,
                timeout=PUSH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            print("DEPLOY_FAIL")
            print(f"`weni project push` timed out after {PUSH_TIMEOUT_SECONDS}s")
            raise SystemExit(1)
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0 or any(marker in output for marker in FAILURE_MARKERS):
            print("DEPLOY_FAIL")
            print(output[-2000:])
            raise SystemExit(1)
        print(output[-800:])

    record_deployment(args.target, project)
    print("DEPLOY_OK")
    print(f"{args.target} recorded as deployed to project {project}")


if __name__ == "__main__":
    main()

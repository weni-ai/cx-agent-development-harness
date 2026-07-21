"""Run the Weni agent evaluation suite and capture the results.

Drives `weni eval run` using the project virtual environment, then writes the
captured output to the run's 04-tests.md artifact and a persistent log file.
This keeps verbose evaluation output out of the agents' context windows.

Usage:
    python .claude/scripts/run_eval.py --run-dir <dir>
    python .claude/scripts/run_eval.py --latest --filter "greeting" --verbose
"""

# Standard library
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Local
from _common import agent_dir, latest_open_run, load_state, venv_bin


def resolve_run_dir(args: argparse.Namespace) -> Path:
    """Resolve the target run directory from explicit path or --latest."""
    if args.run_dir:
        return Path(args.run_dir)
    run_dir = latest_open_run()
    if run_dir is None:
        raise SystemExit("No open run found. Pass --run-dir explicitly.")
    return run_dir


def main() -> None:
    """Run the evaluation suite and persist its output."""
    parser = argparse.ArgumentParser(description="Run weni eval and capture results.")
    parser.add_argument("--run-dir", help="Target run directory.")
    parser.add_argument("--latest", action="store_true", help="Use the latest open run.")
    parser.add_argument(
        "--target",
        help="Collaborator slug to evaluate (folder agents/<slug>/). "
        "Defaults to the target recorded on the run.",
    )
    parser.add_argument("--filter", help="Filter to specific tests.")
    parser.add_argument("--verbose", action="store_true", help="Pass --verbose to weni eval.")
    args = parser.parse_args()

    run_dir = resolve_run_dir(args)
    target = args.target or load_state(run_dir).get("target")
    weni = venv_bin("weni")
    if not weni.exists():
        raise SystemExit("weni CLI not found in .venv. Run bootstrap_env.py first.")

    command = [str(weni), "eval", "run"]
    if args.filter:
        command += ["--filter", args.filter]
    if args.verbose:
        command += ["--verbose"]

    result = subprocess.run(command, cwd=str(agent_dir(target)), capture_output=True, text=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    status = "PASS" if result.returncode == 0 else "FAIL"

    report_content = (
        f"# Test Results\n\n"
        f"Command: `{' '.join(command)}`\n"
        f"Run at: {timestamp}\n"
        f"Status: {status} (exit code {result.returncode})\n\n"
        f"## Output\n\n```\n{output.strip()}\n```\n"
    )

    artifact = Path(run_dir) / "artifacts" / "03-tests.md"
    artifact.write_text(report_content, encoding="utf-8")

    log_file = Path(run_dir) / "logs" / "03-test-tester.log"
    log_file.write_text(output, encoding="utf-8")

    print(f"EVAL_{status}")
    print(f"Artifact: {artifact}")
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()

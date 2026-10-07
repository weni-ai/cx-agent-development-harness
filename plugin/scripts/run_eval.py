"""Run one round of the Weni agent evaluation and capture it as a numbered artifact.

Each call runs `weni eval run --verbose` (the judge's reasoning is needed to triage
failures) inside `agents/<target>/` and writes `<RUN_DIR>/artifacts/03-eval-run-<N>.md`
plus `logs/03-eval-run-<N>.log`. It never touches `03-tests.md`, which belongs to
the tester and holds the triage.

Full rounds (no --filter) are capped by --max-rounds so the eval loop always ends;
filtered re-runs (flakiness checks) do not count toward the cap.

Prints one of: EVAL_PASS, EVAL_FAIL, EVAL_TIMEOUT, EVAL_ROUND_LIMIT.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_eval.py --run-dir <dir>
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_eval.py --latest --filter "greeting"
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_eval.py --run-dir <dir> --max-rounds 5
"""

from __future__ import annotations

# Standard library
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Local
from _common import agent_dir, latest_open_run, load_state, venv_bin
from check_ready import ensure_ready

DEFAULT_MAX_ROUNDS = 3
DEFAULT_TIMEOUT_SECONDS = 1200
FAILURE_MARKERS = ("Traceback (most recent call last)",)
EXIT_ROUND_LIMIT = 3


def resolve_run_dir(args: argparse.Namespace) -> Path:
    """Resolve the target run directory from explicit path or --latest."""
    if args.run_dir:
        return Path(args.run_dir)
    run_dir = latest_open_run()
    if run_dir is None:
        raise SystemExit("No open run found. Pass --run-dir explicitly.")
    return run_dir


def previous_runs(artifacts: Path) -> list[Path]:
    """Return the existing eval-run artifacts in round order."""
    return sorted(artifacts.glob("03-eval-run-*.md"), key=lambda path: int(path.stem.rsplit("-", 1)[1]))


def is_full_round(artifact: Path) -> bool:
    """Return True when an eval-run artifact ran the whole suite (no filter)."""
    return "Filter: none" in artifact.read_text(encoding="utf-8")


def main() -> None:
    """Run one eval round and persist its output."""
    parser = argparse.ArgumentParser(description="Run one weni eval round and capture results.")
    parser.add_argument("--run-dir", help="Target run directory.")
    parser.add_argument("--latest", action="store_true", help="Use the latest open run.")
    parser.add_argument("--target", help="Collaborator slug. Defaults to the run's target.")
    parser.add_argument("--filter", help="Only run matching tests (flakiness re-check).")
    parser.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS, help="Cap on full rounds.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Seconds before aborting.")
    args = parser.parse_args()

    run_dir = resolve_run_dir(args)
    artifacts = run_dir / "artifacts"
    existing = previous_runs(artifacts)
    full_rounds = sum(1 for path in existing if is_full_round(path))
    if not args.filter and full_rounds >= args.max_rounds:
        print("EVAL_ROUND_LIMIT")
        print(f"{full_rounds} full eval rounds already ran (cap {args.max_rounds}). Ask the user how to proceed.")
        raise SystemExit(EXIT_ROUND_LIMIT)

    ensure_ready()
    target = args.target or load_state(run_dir).get("target")
    command = [str(venv_bin("weni")), "eval", "run", "--verbose"]
    if args.filter:
        command += ["--filter", args.filter]

    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        result = subprocess.run(
            command, cwd=str(agent_dir(target)), capture_output=True, text=True, timeout=args.timeout
        )
        output = result.stdout + ("\n" + result.stderr if result.stderr else "")
        failed = result.returncode != 0 or any(marker in output for marker in FAILURE_MARKERS)
        status = "FAIL" if failed else "PASS"
        exit_code = result.returncode or (1 if failed else 0)
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or "") if isinstance(error.stdout, str) else ""
        status, exit_code = "TIMEOUT", 124

    round_number = len(existing) + 1
    artifact = artifacts / f"03-eval-run-{round_number}.md"
    artifact.write_text(
        f"# Eval run {round_number}\n\n"
        f"- Status: {status}\n"
        f"- Filter: {args.filter or 'none'}\n"
        f"- Full round: {full_rounds + (0 if args.filter else 1)} of max {args.max_rounds}\n"
        f"- Run at: {started}\n"
        f"- Command: `weni eval run --verbose{' --filter ' + args.filter if args.filter else ''}`\n\n"
        f"## Output\n\n```\n{output.strip()}\n```\n",
        encoding="utf-8",
    )
    (run_dir / "logs" / f"03-eval-run-{round_number}.log").write_text(output, encoding="utf-8")

    print(f"EVAL_{status}")
    print(f"Artifact: {artifact}")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

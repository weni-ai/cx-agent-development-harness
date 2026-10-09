"""Deterministic readiness gate: is the Weni CLI installed, logged in, and pointed at a project?

No pipeline may start until this returns READY. `init_run.py` enforces it, and the
tool-test and eval runners re-check it because a token can expire mid-run. This
script never runs `weni login` (an interactive browser OAuth flow); it only tells
the user the exact command to run.

States (exit code):
    READY                 0   pipeline may start
    AUTH_REQUIRED        10   user must run `weni login`
    PROJECT_NOT_SELECTED 11   user must run `weni project use <uuid>`
    PROBE_ERROR          12   the CLI answered something unexpected (output shown)
    NOT_INSTALLED        20   .venv or weni-cli missing (init_run.py installs it)

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_ready.py
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_ready.py --hook   # SessionStart context (never fails)
"""

from __future__ import annotations

# Standard library
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

# Local
from _common import agents_root, latest_open_run, project_root, runs_dir, venv_bin
from update_check import update_notice

EXIT_CODES = {
    "READY": 0,
    "AUTH_REQUIRED": 10,
    "PROJECT_NOT_SELECTED": 11,
    "PROBE_ERROR": 12,
    "NOT_INSTALLED": 20,
}

FIXES = {
    "READY": "Weni CLI is logged in and a project is selected.",
    "AUTH_REQUIRED": "Log in once (browser OAuth). In Claude Code type: "
    "`! .venv/bin/weni login` — in any other terminal: `.venv/bin/weni login`.",
    "PROJECT_NOT_SELECTED": "Select the Weni project: `printf 'q\\n' | .venv/bin/weni project list`, "
    "then `.venv/bin/weni project use <project-uuid>`.",
    "PROBE_ERROR": "The Weni CLI returned an unexpected answer (see output below). "
    "Run `/weni:status` to see it again.",
    "NOT_INSTALLED": "This folder is not set up for Weni yet: run `/weni:setup`, or go straight "
    "to `/weni:new-agent`, which sets it up automatically (about 1 minute).",
}

# Substrings (lowercase) in the CLI output. Tune them here if the CLI wording
# changes; dev/tests/test_readiness.py pins the expected behavior.
AUTH_MARKERS = ("missing login", "please login", "not logged", "unauthorized", "not authenticated", "expired")
PROJECT_MARKERS = ("current project: none", "no project")

PROBE_TIMEOUT_SECONDS = 60
CACHE_TTL_SECONDS = 15 * 60
WENI_CONFIG = Path.home() / ".weni_cli"
CACHE_FILE = project_root() / ".harness" / "runs" / ".ready-cache"


def run_weni(*args: str, stdin: str = "") -> tuple[int, str]:
    """Run a weni command non-interactively and return (returncode, output)."""
    try:
        result = subprocess.run(
            [str(venv_bin("weni")), *args],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return 124, f"`weni {' '.join(args)}` timed out after {PROBE_TIMEOUT_SECONDS}s"
    return result.returncode, (result.stdout + result.stderr).strip()


def token_recently_verified() -> bool:
    """True when the server accepted the token within the cache window."""
    return CACHE_FILE.exists() and time.time() - CACHE_FILE.stat().st_mtime < CACHE_TTL_SECONDS


def probe(validate_token: bool = True) -> tuple[str, str]:
    """Return (state, raw CLI output) for the current environment.

    `weni project current` only reads local config, so the token is validated
    against the server with `weni project list` (slow, ~20s; cached 15 minutes).
    `validate_token=False` skips that network call (session-start hook).
    """
    if not venv_bin("weni").exists():
        return "NOT_INSTALLED", ""
    if not WENI_CONFIG.exists():
        return "AUTH_REQUIRED", ""

    if validate_token and not token_recently_verified():
        code, output = run_weni("project", "list", stdin="q\n")  # "q" ends its pager
        if any(marker in output.lower() for marker in AUTH_MARKERS):
            return "AUTH_REQUIRED", output
        if code != 0:
            return "PROBE_ERROR", output
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.touch()

    code, output = run_weni("project", "current")
    lowered = output.lower()
    if any(marker in lowered for marker in AUTH_MARKERS):
        return "AUTH_REQUIRED", output
    if any(marker in lowered for marker in PROJECT_MARKERS):
        return "PROJECT_NOT_SELECTED", output
    if code != 0:
        return "PROBE_ERROR", output
    return "READY", output


def current_project() -> str:
    """Return the selected Weni project uuid (empty when none or unreadable)."""
    _, output = run_weni("project", "current")
    match = re.search(r"current project:\s*(\S+)", output, re.IGNORECASE)
    project = match.group(1) if match else ""
    return "" if project.lower() == "none" else project


def ensure_ready() -> None:
    """Exit with the gate's code unless the environment is READY (used by other scripts)."""
    state, output = probe()
    if state != "READY":
        print(state)
        print(FIXES[state])
        if output and state == "PROBE_ERROR":
            print(output[-1500:])
        raise SystemExit(EXIT_CODES[state])


def is_harness_project() -> bool:
    """True when the session's folder already holds Weni agents or harness runs."""
    return runs_dir().exists() or any(agents_root().glob("*/agent_definition.yaml"))


def hook_message() -> str:
    """Build the session-start context; empty outside Weni agent projects."""
    if not is_harness_project():
        return ""
    state, _ = probe(validate_token=False)
    lines = [f"[weni] Readiness (local check): {state}. {FIXES[state]}"]
    run_dir = latest_open_run()
    if run_dir is not None:
        lines.append(f"[weni] Open run: {run_dir}. To continue it, follow the weni:pipeline skill.")
    return "\n".join(lines)


def main() -> None:
    """Probe readiness and report it for a human, an agent, or a session hook."""
    parser = argparse.ArgumentParser(description="Check Weni CLI readiness.")
    parser.add_argument("--hook", action="store_true", help="Emit session-start context; never fails.")
    args = parser.parse_args()

    if args.hook:
        context = hook_message()
        notice = update_notice() if context else ""
        if notice:  # JSON so the user sees the notice; Claude still gets the context
            print(json.dumps({"systemMessage": notice, "hookSpecificOutput": {
                "hookEventName": "SessionStart", "additionalContext": f"{context}\n[weni] {notice}"}}))
        else:
            print(context)
        return  # hooks never fail the session; the real gate is init_run.py

    state, output = probe()

    print(state)
    print(FIXES[state])
    if output and state == "PROBE_ERROR":
        print(output[-1500:])
    raise SystemExit(EXIT_CODES[state])


if __name__ == "__main__":
    main()

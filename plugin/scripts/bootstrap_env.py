"""Prepare the user's project: .venv with weni-cli, a safe .gitignore, the deploy ask rule, then the readiness gate.

init_run.py calls these helpers automatically on the first run in a folder; running
this script directly is only needed to repair or upgrade the environment.

Never runs `weni login` (interactive browser OAuth); the readiness gate tells the
user the exact command instead.

Exit codes: the readiness gate's codes (see check_ready.py), or 30 on install failure.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap_env.py
"""

from __future__ import annotations

# Standard library
import json
import subprocess
import sys
import venv
from pathlib import Path

# Local
from _common import project_root, venv_bin
from check_ready import ensure_ready

EXIT_SETUP_ERROR = 30

# Never commit the venv, local secrets, run history, or verbose test output.
GITIGNORE_ENTRIES = (
    ".venv/", "**/.env", "**/.globals", ".harness/", "**/test-results.md", "__pycache__/",
    ".claude/settings.local.json",
)

# deploy.py publishes to the live Manager. An ask rule makes Claude Code prompt for it
# even in auto mode, whose classifier would otherwise deny it as a production deploy.
# Independent of the plugin version in the cache path and of the quotes around it.
DEPLOY_ASK_RULE = "Bash(python3 *scripts/deploy.py*)"


def ensure_venv() -> None:
    """Create the project virtual environment if it does not exist."""
    venv_dir = project_root() / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment at .venv ...")
        venv.create(str(venv_dir), with_pip=True)


def install_cli() -> None:
    """Install or upgrade weni-cli (and PyYAML for the harness scripts) inside the venv."""
    print("Installing/upgrading weni-cli ...")
    result = subprocess.run(
        [str(venv_bin("pip")), "install", "--upgrade", "weni-cli", "pyyaml"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(EXIT_SETUP_ERROR)


def ensure_gitignore() -> None:
    """Append any missing harness entries to the project's .gitignore."""
    gitignore = project_root() / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    missing = [entry for entry in GITIGNORE_ENTRIES if entry not in existing]
    if missing:
        block = ["", "# Weni harness"] if existing else ["# Weni harness"]
        gitignore.write_text("\n".join(existing + block + missing) + "\n", encoding="utf-8")
        print(f"Added to .gitignore: {', '.join(missing)}")


def ensure_deploy_ask_rule() -> None:
    """Merge the deploy ask rule into .claude/settings.local.json, keeping everything else."""
    settings_path = project_root() / ".claude" / "settings.local.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    except json.JSONDecodeError:
        print(f"Warning: {settings_path} is not valid JSON; add \"{DEPLOY_ASK_RULE}\" to permissions.ask yourself.")
        return
    permissions = settings.setdefault("permissions", {})
    ask = permissions.setdefault("ask", [])
    if DEPLOY_ASK_RULE in ask:
        return
    ask.append(DEPLOY_ASK_RULE)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    print(f"Added to .claude/settings.local.json: permissions.ask {DEPLOY_ASK_RULE}")


def report_agents() -> None:
    """Print where this folder's agents are (discover_agents.py, run with the .venv's PyYAML)."""
    script = Path(__file__).resolve().parent / "discover_agents.py"
    subprocess.run([str(venv_bin("python")), str(script)], cwd=str(project_root()), check=False)


def main() -> None:
    """Install the environment and report readiness."""
    ensure_gitignore()
    ensure_deploy_ask_rule()
    ensure_venv()
    install_cli()
    report_agents()
    ensure_ready()
    print("READY")


if __name__ == "__main__":
    main()

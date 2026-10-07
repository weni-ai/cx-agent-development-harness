"""Prepare the user's project: .venv with weni-cli, a safe .gitignore, then the readiness gate.

Never runs `weni login` (interactive browser OAuth); the readiness gate tells the
user the exact command instead.

Exit codes: the readiness gate's codes (see check_ready.py), or 30 on install failure.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap_env.py
"""

from __future__ import annotations

# Standard library
import subprocess
import sys
import venv

# Local
from _common import project_root, venv_bin
from check_ready import ensure_ready

EXIT_SETUP_ERROR = 30

# Never commit the venv, local secrets, run history, or verbose test output.
GITIGNORE_ENTRIES = (".venv/", "**/.env", "**/.globals", ".harness/", "**/test-results.md", "__pycache__/")


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


def main() -> None:
    """Install the environment and report readiness."""
    ensure_gitignore()
    ensure_venv()
    install_cli()
    ensure_ready()
    print("READY")


if __name__ == "__main__":
    main()

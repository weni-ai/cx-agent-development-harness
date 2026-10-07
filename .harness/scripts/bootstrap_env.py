"""Create the project .venv, install weni-cli, then run the readiness gate.

Never runs `weni login` (interactive browser OAuth); the readiness gate tells the
user the exact command instead.

Exit codes: the readiness gate's codes (see check_ready.py), or 30 on install failure.

Usage:
    python3 .harness/scripts/bootstrap_env.py
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


def main() -> None:
    """Install the environment and report readiness."""
    ensure_venv()
    install_cli()
    ensure_ready()
    print("READY")


if __name__ == "__main__":
    main()

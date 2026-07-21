"""Bootstrap the project environment and probe Weni authentication.

Two responsibilities:
  1. Non-interactive: ensure a .venv exists and weni-cli is installed.
  2. Auth probe: check whether the Weni CLI session is valid (token stored in
     ~/.weni_cli). This script NEVER runs `weni login` itself, because that is an
     interactive browser OAuth flow that must be completed by the user.

Exit codes:
    0   AUTHENTICATED  -> pipeline may continue
    10  AUTH_REQUIRED  -> the user must run `weni login` once
    20  setup error    -> venv / install failure
"""

# Standard library
import argparse
import subprocess
import sys
import venv

# Local
from _common import project_root, venv_bin

EXIT_AUTHENTICATED = 0
EXIT_AUTH_REQUIRED = 10
EXIT_SETUP_ERROR = 20


def ensure_venv() -> None:
    """Create the project virtual environment if it does not exist."""
    venv_dir = project_root() / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment at .venv ...")
        venv.create(str(venv_dir), with_pip=True)


def install_cli() -> None:
    """Install or upgrade weni-cli inside the virtual environment."""
    pip = venv_bin("pip")
    print("Installing/upgrading weni-cli ...")
    result = subprocess.run(
        [str(pip), "install", "--upgrade", "weni-cli"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(EXIT_SETUP_ERROR)


def auth_probe() -> bool:
    """Return True if the Weni CLI reports a valid authenticated session."""
    weni = venv_bin("weni")
    if not weni.exists():
        return False
    result = subprocess.run(
        [str(weni), "project", "current"],
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).lower()
    if result.returncode != 0:
        return False
    auth_failure_markers = ("not authenticated", "login", "unauthorized", "token")
    return not any(marker in output for marker in auth_failure_markers)


def main() -> None:
    """Run setup steps and the auth probe, reporting a machine-readable status."""
    parser = argparse.ArgumentParser(description="Bootstrap env and probe Weni auth.")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Only run the auth probe (assume venv and CLI already exist).",
    )
    args = parser.parse_args()

    if not args.skip_install:
        ensure_venv()
        install_cli()

    if auth_probe():
        print("AUTHENTICATED")
        raise SystemExit(EXIT_AUTHENTICATED)

    print("AUTH_REQUIRED")
    print("Run once in your terminal: source .venv/bin/activate && weni login")
    raise SystemExit(EXIT_AUTH_REQUIRED)


if __name__ == "__main__":
    main()

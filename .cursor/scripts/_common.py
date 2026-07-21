"""Shared helpers for the Weni harness deterministic script layer.

These utilities resolve project paths, locate the virtual environment binaries,
and read/write the run state. Keeping them here avoids duplicating logic across
the individual scripts (init_run, update_state, run_eval, etc.).
"""

# Standard library
import json
import os
import re
from datetime import datetime
from pathlib import Path

PHASES = [
    {"num": "00", "key": "intake", "name": "Intake", "agent": "orchestrator", "artifact": "00-intake.md", "optional": False},
    {"num": "01", "key": "plan", "name": "Plan", "agent": "planner", "artifact": "01-plan.md", "optional": False},
    {"num": "02", "key": "implement", "name": "Implement", "agent": "implementer", "artifact": "02-implementation.md", "optional": False},
    {"num": "03", "key": "test", "name": "Test", "agent": "tester", "artifact": "03-tests.md", "optional": False},
    {"num": "04", "key": "review", "name": "Review", "agent": "reviewer", "artifact": "04-review.md", "optional": False},
    {"num": "05", "key": "docs", "name": "Docs", "agent": "docs-writer", "artifact": "05-docs.md", "optional": False},
]

VALID_STATUSES = ("pending", "in-progress", "done", "failed", "skipped")
OPEN_STATUSES = ("pending", "in-progress")


def project_root() -> Path:
    """Return the project root (two levels above the .cursor/scripts folder)."""
    return Path(__file__).resolve().parents[2]


def runs_dir() -> Path:
    """Return the directory that holds all runs."""
    return project_root() / ".cursor" / "runs"


def agents_root() -> Path:
    """Return the workspace directory that holds every collaborator agent.

    Each collaborator lives in its own subfolder (`agents/<slug>/`) at the same
    level as .cursor, with its own `agent_definition.yaml`, `tools/`, and eval.
    A project with a single agent simply has one subfolder. This keeps the agent
    code isolated from the harness config and lets `weni project push` run from a
    single collaborator folder so only that agent is uploaded to CX Platform.
    """
    return project_root() / "agents"


def list_agent_slugs() -> list[str]:
    """Return the slugs of every collaborator folder that holds a definition."""
    root = agents_root()
    if not root.exists():
        return []
    slugs = [
        path.name
        for path in sorted(root.iterdir())
        if path.is_dir() and (path / "agent_definition.yaml").exists()
    ]
    return slugs


def resolve_agent_dir(slug: str | None = None) -> Path:
    """Resolve a single collaborator folder under `agents/`.

    With an explicit slug, return `agents/<slug>` (whether or not it exists yet,
    so the implementer can create it). Without a slug, auto-detect when exactly
    one collaborator exists; otherwise raise, asking the caller to pass --target.
    """
    if slug:
        return agents_root() / slug

    slugs = list_agent_slugs()
    if len(slugs) == 1:
        return agents_root() / slugs[0]
    if not slugs:
        raise SystemExit(
            "No collaborator agent found under agents/. Pass --target <slug> "
            "(the implementer creates agents/<slug>/ on first run)."
        )
    raise SystemExit(
        "Multiple collaborator agents found under agents/: "
        + ", ".join(slugs)
        + ". Pass --target <slug> to select one."
    )


def agent_dir(slug: str | None = None) -> Path:
    """Backward-compatible alias that resolves a single collaborator folder."""
    return resolve_agent_dir(slug)


def venv_bin(name: str) -> Path:
    """Return the path to an executable inside the project virtual environment."""
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return project_root() / ".venv" / bin_dir / f"{name}{suffix}"


def slugify(text: str) -> str:
    """Convert free text into a short, filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    words = slug.split("-")
    return "-".join(words[:6]) or "run"


def state_json_path(run_dir: Path) -> Path:
    """Return the path to the machine-readable run state file."""
    return Path(run_dir) / "STATE.json"


def state_md_path(run_dir: Path) -> Path:
    """Return the path to the human-readable run state snapshot."""
    return Path(run_dir) / "STATE.md"


def load_state(run_dir: Path) -> dict:
    """Load the machine-readable run state."""
    with open(state_json_path(run_dir), "r", encoding="utf-8") as state_file:
        return json.load(state_file)


def save_state(run_dir: Path, state: dict) -> None:
    """Persist the run state to STATE.json and re-render STATE.md."""
    state["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(state_json_path(run_dir), "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=2)
    render_state_md(run_dir, state)


def current_phase_label(state: dict) -> str:
    """Return a readable label for the first non-completed phase."""
    for phase in state["phases"]:
        if phase["status"] in OPEN_STATUSES:
            return f"{int(phase['num'])}. {phase['name']}"
    return "complete"


def render_state_md(run_dir: Path, state: dict) -> None:
    """Render STATE.md from the machine-readable state (whole-file rewrite)."""
    rows = []
    for phase in state["phases"]:
        artifact = phase["artifact"] if phase["status"] == "done" else "—"
        rows.append(
            f"| {int(phase['num'])} | {phase['name']:<9} | {phase['agent']:<12} | "
            f"{phase['status']:<11} | {artifact} |"
        )
    table = "\n".join(rows)

    blockers = state.get("blockers") or []
    blockers_md = "\n".join(f"- {item}" for item in blockers) if blockers else "- None"

    lines = [
        f"# Run State — {state['run_id']}",
        "",
        f"Feature: {state['feature']}",
        f"Target agent: {state.get('target', '—')}",
        f"Mode: {state.get('mode', 'standard')}",
        f"Started: {state['started']} | Updated: {state['updated']}",
        f"Current phase: {current_phase_label(state)} | Checkpoint: {state.get('checkpoint', '—')}",
        "",
        "## Phases",
        "| # | Phase     | Agent        | Status      | Artifact          |",
        "|---|-----------|--------------|-------------|-------------------|",
        table,
        "",
        "## Current focus",
        state.get("focus", "—"),
        "",
        "## Open decisions / blockers",
        blockers_md,
        "",
        "## Resume hint",
        state.get("resume_hint", "—"),
        "",
    ]
    with open(state_md_path(run_dir), "w", encoding="utf-8") as md_file:
        md_file.write("\n".join(lines))


def find_phase(state: dict, selector: str) -> dict:
    """Find a phase by its numeric prefix (e.g. '02') or key (e.g. 'plan')."""
    selector = selector.lstrip("0") or "0"
    for phase in state["phases"]:
        if phase["key"] == selector or str(int(phase["num"])) == selector:
            return phase
    raise SystemExit(f"Unknown phase selector: {selector}")


def latest_open_run(target: str | None = None) -> Path | None:
    """Return the most recent run directory that still has open phases.

    When `target` is given, only runs whose recorded target agent matches it are
    considered, so collaborators can be resumed independently.
    """
    base = runs_dir()
    if not base.exists():
        return None
    candidates = sorted(
        (path for path in base.iterdir() if path.is_dir() and state_json_path(path).exists()),
        reverse=True,
    )
    for run_dir in candidates:
        state = load_state(run_dir)
        if target and state.get("target") != target:
            continue
        if any(phase["status"] in OPEN_STATUSES for phase in state["phases"]):
            return run_dir
    return None

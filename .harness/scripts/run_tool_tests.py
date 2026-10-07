"""Run local tool tests with verbose output, saved per tool.

Runs `weni run agent_definition.yaml <agent_name> <tool_name> -v` for every tool
defined in the agent (or for a specific tool if --tool is given). The verbose
output of each tool is saved to `agents/<slug>/tools/<tool>/test-results.md`, so
re-testing one tool never clobbers the results of the others. A slim summary
table (status per tool, no verbose output) is rebuilt at
`agents/<slug>/test-results.md` from the per-tool files after every run.

A tool FAILS when `weni run` exits non-zero OR its output contains a failure
marker (e.g. a Python traceback): the CLI can exit 0 even when the tool crashed.

This is distinct from `weni eval run`, which runs the full evaluation suite.

Usage:
    python .harness/scripts/run_tool_tests.py --target <slug>
    python .harness/scripts/run_tool_tests.py --target <slug> --tool <tool_key>
"""

from __future__ import annotations

# Standard library
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Third-party
try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required. Run this script with the project .venv python.")

# Local
from _common import agent_dir, venv_bin
from check_ready import ensure_ready

# Output substrings that mean the tool crashed even if `weni run` exited 0.
FAILURE_MARKERS = ("Traceback (most recent call last)",)


def load_agent_definition(definition_path: Path) -> dict:
    """Load and return the agent definition YAML."""
    with open(definition_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def collect_tools(definition: dict, agent_filter: str | None = None) -> list[tuple[str, str, str]]:
    """Return a list of (agent_key, tool_key, tool_folder) triples to test.

    Each triple corresponds to one `weni run` invocation. The folder comes from
    the tool's `source.path` when present, defaulting to `tools/<tool_key>`.
    """
    triples = []
    for agent_key, agent in (definition.get("agents") or {}).items():
        if agent_filter and agent_key != agent_filter:
            continue
        for tool_entry in (agent.get("tools") or []):
            for tool_key, tool_config in tool_entry.items():
                source = (tool_config or {}).get("source") or {}
                folder = source.get("path") or f"tools/{tool_key}"
                triples.append((agent_key, tool_key, folder))
    return triples


def run_tool(weni: Path, definition_file: str, agent_key: str, tool_key: str, cwd: Path) -> tuple[str, bool]:
    """Run a single tool test with verbose flag and return (output, passed)."""
    command = [str(weni), "run", definition_file, agent_key, tool_key, "-v"]
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    combined = result.stdout + ("\n" + result.stderr if result.stderr else "")
    passed = result.returncode == 0 and not any(marker in combined for marker in FAILURE_MARKERS)
    return combined, passed


def write_tool_result(
    root: Path, folder: str, agent_key: str, tool_key: str, status: str, timestamp: str, output: str
) -> Path:
    """Write one tool's verbose results to agents/<slug>/<folder>/test-results.md."""
    tool_dir = root / folder
    tool_dir.mkdir(parents=True, exist_ok=True)
    results_file = tool_dir / "test-results.md"
    results_file.write_text(
        f"# Tool test — {agent_key} / {tool_key}\n\n"
        f"- Status: {status}\n"
        f"- Run at: {timestamp}\n"
        f"- Command: `weni run agent_definition.yaml {agent_key} {tool_key} -v`\n\n"
        f"## Verbose output\n\n"
        f"```\n{output.strip()}\n```\n",
        encoding="utf-8",
    )
    return results_file


def read_tool_result_header(results_file: Path) -> dict:
    """Parse the metadata header of a per-tool test-results.md file."""
    info = {"agent": "?", "tool": results_file.parent.name, "status": "?", "run_at": "?"}
    for line in results_file.read_text(encoding="utf-8").splitlines()[:8]:
        if line.startswith("# Tool test — "):
            parts = line.removeprefix("# Tool test — ").split(" / ")
            if len(parts) == 2:
                info["agent"], info["tool"] = parts[0].strip(), parts[1].strip()
        elif line.startswith("- Status: "):
            info["status"] = line.removeprefix("- Status: ").strip()
        elif line.startswith("- Run at: "):
            info["run_at"] = line.removeprefix("- Run at: ").strip()
    return info


def write_summary(root: Path, timestamp: str) -> Path:
    """Rebuild the agent-level summary table from every per-tool results file.

    The summary carries no verbose output; details live next to each tool. It is
    rebuilt from disk so partial runs (--tool) keep the other tools' rows.
    """
    rows = []
    summary_file = root / "test-results.md"
    per_tool_files = sorted(path for path in root.rglob("test-results.md") if path != summary_file)
    for results_file in per_tool_files:
        info = read_tool_result_header(results_file)
        relative = results_file.relative_to(root).as_posix()
        rows.append(
            f"| {info['agent']} | {info['tool']} | {info['status']} | {info['run_at']} | "
            f"[{relative}]({relative}) |"
        )
    summary_file.write_text(
        "# Local Tool Test Results — summary\n\n"
        f"Updated: {timestamp}\n\n"
        "Verbose output lives next to each tool (`<tool folder>/test-results.md`).\n\n"
        "| Agent | Tool | Status | Last run | Details |\n"
        "|-------|------|--------|----------|---------|\n"
        + "\n".join(rows)
        + "\n",
        encoding="utf-8",
    )
    return summary_file


def main() -> None:
    """Run the selected tool tests, write per-tool results, and rebuild the summary."""
    parser = argparse.ArgumentParser(description="Run local weni tool tests and save verbose output per tool.")
    parser.add_argument(
        "--target",
        help="Collaborator slug to test (folder agents/<slug>/). "
        "Optional when the project has a single agent.",
    )
    parser.add_argument("--tool", help="Only test this tool key.")
    parser.add_argument("--agent", help="Only test tools from this agent key inside the definition.")
    args = parser.parse_args()

    root = agent_dir(args.target)
    definition_path = root / "agent_definition.yaml"
    if not definition_path.exists():
        raise SystemExit(f"agent_definition.yaml not found at {definition_path}")

    ensure_ready()
    weni = venv_bin("weni")
    definition = load_agent_definition(definition_path)
    tool_triples = collect_tools(definition, agent_filter=args.agent)

    if args.tool:
        tool_triples = [(a, t, f) for a, t, f in tool_triples if t == args.tool]

    if not tool_triples:
        raise SystemExit("No tools found to test. Check agent_definition.yaml or your --tool/--agent filters.")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall_pass = True

    for agent_key, tool_key, folder in tool_triples:
        output, passed = run_tool(weni, "agent_definition.yaml", agent_key, tool_key, root)
        status = "PASS" if passed else "FAIL"
        overall_pass = overall_pass and passed
        write_tool_result(root, folder, agent_key, tool_key, status, timestamp, output)
        print(f"  {status}  {agent_key}/{tool_key}")

    summary_file = write_summary(root, timestamp)

    overall_status = "ALL_PASS" if overall_pass else "SOME_FAIL"
    print(f"\n{overall_status}")
    print(f"Summary: {summary_file}")
    raise SystemExit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()

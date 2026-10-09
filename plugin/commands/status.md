---
description: Show Weni readiness, the open run, and the agents in this project
---

Report, in at most 10 lines: the output of `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_ready.py"`,
the open run from `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_run.py" --latest-open` (with its
current phase and blockers from `STATE.md`), the agents from
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/discover_agents.py"` (flag any `LOOSE`/`INVALID`), and the
plugin version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. Then suggest the
single next step. Do not start or change anything.

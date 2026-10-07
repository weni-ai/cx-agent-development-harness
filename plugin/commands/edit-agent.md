---
description: Modify an existing Weni collaborator agent (delta plan, targeted re-tests)
argument-hint: <slug> <what to change>
---

Modify an existing Weni collaborator agent: $ARGUMENTS

Read `${CLAUDE_PLUGIN_ROOT}/skills/pipeline/SKILL.md` and follow it from "Start": run
the readiness gate, confirm the agent's files exist under `agents/<slug>/` (if not, ask
the user to copy them there first), create the run with `--mode edit`, and begin at
Intake by recording the current structure as a baseline.

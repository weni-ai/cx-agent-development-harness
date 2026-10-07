---
description: Build a new Weni collaborator agent (full gated pipeline)
argument-hint: <what the agent should do>
---

Build a new Weni collaborator agent: $ARGUMENTS

Read `${CLAUDE_PLUGIN_ROOT}/skills/pipeline/SKILL.md` and follow it from "Start": run
the readiness gate, pick a short kebab-case slug (confirm it with the user), create the
run with `--mode new`, and begin at Intake. If the request above is empty, first ask
the user what the agent should do.

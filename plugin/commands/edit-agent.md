---
description: Modify an existing Weni collaborator agent (delta plan, targeted re-tests)
argument-hint: [slug] <what to change>
---

Modify an existing Weni collaborator agent: $ARGUMENTS

Read `${CLAUDE_PLUGIN_ROOT}/skills/pipeline/SKILL.md` and follow it from "Start": run
`discover_agents.py` (moving any agents found outside `agents/` into it with
`adopt_agent.py` after the user confirms), pick the target from the agents now under
`agents/` (ask if the slug is missing or ambiguous), create the run with `--mode edit`,
and begin at Intake by recording the current structure as a baseline.

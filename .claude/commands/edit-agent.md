---
description: Start the pipeline to modify an existing collaborator agent
argument-hint: <slug> <what to change>
---

Modify an existing collaborator agent: $ARGUMENTS

Follow AGENTS.md: run the readiness gate, confirm the agent's files exist under
`agents/<slug>/` (if not, ask the user to copy them there first), create the run with
`--mode edit`, and start at Intake by recording the current structure as a baseline.

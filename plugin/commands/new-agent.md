---
description: Build a new Weni collaborator agent (full gated pipeline). Sets the folder up first if needed.
argument-hint: <what the agent should do>
---

Build a new Weni collaborator agent: $ARGUMENTS

Read `${CLAUDE_PLUGIN_ROOT}/skills/pipeline/SKILL.md` and follow it from "Start": pick
a short kebab-case slug (confirm it with the user) and create the run with
`--mode new`. If this folder was never set up, that run installs everything by itself
(about a minute), stopping only for the Weni login and the project choice. Then begin
at Intake. If the request above is empty, first ask the user what the agent should do.

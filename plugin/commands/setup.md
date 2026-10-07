---
description: Set up this folder for Weni and build a new collaborator agent (full gated pipeline)
argument-hint: <what the agent should do>
---

Set up this folder and build a new Weni collaborator agent: $ARGUMENTS

Read `${CLAUDE_PLUGIN_ROOT}/skills/pipeline/SKILL.md` and follow it from "Start": pick
a short kebab-case slug (confirm it with the user) and create the run with
`--mode new`. In a new folder that run installs everything by itself (.venv,
weni-cli, .gitignore; about a minute), stopping only for the Weni login and the
project choice. Then begin at Intake. If the request above is empty, first ask the
user what the agent should do.

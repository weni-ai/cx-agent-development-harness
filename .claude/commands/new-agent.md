---
description: Start the pipeline to build a new collaborator agent
argument-hint: <what the agent should do>
---

Build a new collaborator agent: $ARGUMENTS

Follow AGENTS.md: run the readiness gate, pick a short kebab-case slug (confirm it
with the user), create the run with `--mode new`, and start at Intake. If the request
above is empty, ask the user what the agent should do first.

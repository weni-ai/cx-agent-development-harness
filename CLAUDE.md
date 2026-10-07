@AGENTS.md

## Claude Code specifics

- Dispatch phase subagents with the Agent tool (`subagent_type` = `planner`,
  `implementer`, `tester`, `reviewer`, `docs-writer`).
- A SessionStart hook already printed the readiness state and any open run; still
  follow "Start of every session" (the scripts are the authoritative gate).
- When login is needed, ask the user to type `! .venv/bin/weni login` in this
  session, then re-run `check_ready.py`.

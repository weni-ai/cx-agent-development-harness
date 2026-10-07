# Changelog

All notable changes for people using the plugin. Format: one line per change under
Breaking / New / Changed / Fixed. Versions follow semver.

## Unreleased

## 2.1.1 — 2026-10-07

### Fixed
- Schema validation and tool tests work when called with the system `python3`
  (they failed with "PyYAML is required" before switching to the project `.venv`).

## 2.1.0 — 2026-10-07

### Changed
- `/weni:setup` again only prepares the project (once, optional) and
  `/weni:new-agent <description>` builds each agent, setting the folder up itself
  if needed. One project can hold many agents.
- The eval now explains it tests the agent deployed in the Weni project, not your
  local files, and asks you to skip it, deploy first (with confirmation), or switch
  to a test project.

### Fixed
- The eval no longer runs against an agent that is not deployed or is out of date
  (`EVAL_NOT_DEPLOYED` / `EVAL_STALE_DEPLOYMENT`), so it cannot "fix" a correct agent
  based on answers from other collaborators.
- Eval rounds where the target agent never answered are discarded instead of
  triggering code or instruction changes.
- Restored the full Weni constitution (it was truncated: evaluation, Retail Setup,
  validation rules, and more were missing).

## 2.0.1 — 2026-10-07

### Changed
- `/weni:new-agent` is now `/weni:setup <description>`: in a new folder it installs
  `weni-cli` into `.venv` and adds `.gitignore` entries by itself, stopping only for
  the Weni login and project choice, then builds the agent.

## 2.0.0 — 2026-10-07

### Breaking
- Distributed as a Claude Code plugin (`/plugin install weni@weni-ai`) instead of a
  template copied into each project. Commands are now `/weni:new-agent`,
  `/weni:edit-agent`, `/weni:status`, `/weni:setup`. Runs live in `.harness/runs/`.
- Cursor edition paused; this version targets Claude Code only.

### New
- Login gate: no pipeline starts until Weni is READY (logged in, project selected).
  The token is validated against the server, not just read from local config.
- Eval loop with triage: each failure is classified as real bug, instruction gap,
  overly strict test, or flaky, with a confidence level. Max 3 rounds; relaxing a
  test always needs your approval.
- `/weni:setup` prepares any folder: `.venv`, `weni-cli`, and `.gitignore` entries.

### Changed
- Eval tests are written around facts (data, tool use, guardrails), not wording.

### Fixed
- Tool tests no longer report PASS when a tool crashed with exit code 0.
- Tool-test summary includes tools with a custom `source.path`.
- Eval results no longer overwrite the tester's report; the eval has a timeout.

## 1.0.0 — 2026-07-21

- Initial template-based harness (Cursor and Claude Code editions).

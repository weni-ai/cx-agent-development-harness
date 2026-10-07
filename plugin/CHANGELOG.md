# Changelog

All notable changes for people using the plugin. Format: one line per change under
Breaking / New / Changed / Fixed. Versions follow semver.

## Unreleased

## 2.0.0 — 2026-10-07

### Breaking
- Distributed as a Claude Code plugin (`/plugin install weni@weni-ai`) instead of a
  template copied into each project. Commands are now `/weni:setup`,
  `/weni:edit-agent`, `/weni:status`. Runs live in `.harness/runs/`.
- Cursor edition paused; this version targets Claude Code only.

### New
- Login gate: no pipeline starts until Weni is READY (logged in, project selected).
  The token is validated against the server, not just read from local config.
- Eval loop with triage: each failure is classified as real bug, instruction gap,
  overly strict test, or flaky, with a confidence level. Max 3 rounds; relaxing a
  test always needs your approval.
- One command to start: `/weni:setup <description>` prepares a new folder by itself
  (installs `weni-cli` into `.venv`, adds `.gitignore` entries), stopping only for
  the Weni login and project choice, then builds the agent.

### Changed
- Eval tests are written around facts (data, tool use, guardrails), not wording.

### Fixed
- Tool tests no longer report PASS when a tool crashed with exit code 0.
- Tool-test summary includes tools with a custom `source.path`.
- Eval results no longer overwrite the tester's report; the eval has a timeout.

## 1.0.0 — 2026-07-21

- Initial template-based harness (Cursor and Claude Code editions).

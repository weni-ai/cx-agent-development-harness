# Weni Agent Harness — plugin source repo

This repo is the source of the `weni` Claude Code plugin and its marketplace. You are
maintaining the harness here, not running it: never build agents in this repo.

## Layout

| Path | What | Shipped to users |
|------|------|------------------|
| `plugin/` | The plugin: `skills/pipeline` (orchestrator), `skills/weni-agents` (Weni rules), `agents/` (phase subagents), `commands/`, `hooks/`, `scripts/` (deterministic gates), `CHANGELOG.md` | yes |
| `.claude-plugin/marketplace.json` | Marketplace `weni-ai` listing `./plugin` | yes (catalog) |
| `dev/` | Maintainer tooling: `harness` CLI, `sandbox.py`, `release.py`, `scenarios/`, `tests/` | no |

## Every change to `plugin/` (do this without being asked)

1. Add one line to `## Unreleased` in `plugin/CHANGELOG.md` under `### Breaking`,
   `### New`, `### Changed`, or `### Fixed`, written for partners (what changes for
   them, not how). Maintainer-only changes (`dev/`) need no entry.
2. Run `dev/harness test` (self-tests + `claude plugin validate`); it fails if
   `plugin/` changed since the last release tag and `## Unreleased` is empty.
3. Never edit `version` by hand. Releases are cut only when the user asks:
   `dev/harness release` infers the bump (Breaking → major, New → minor, else patch),
   commits, and tags locally. Pushing is the user's decision; users only receive an
   update when `version` changes.

## Improvement loop

1. `dev/harness sandbox new <scenario>` (`weather-simple`, `order-status-medium`,
   `weather-edit`) creates an empty project in `~/.harness-sandboxes/`.
2. The user opens it with `claude --plugin-dir <this repo>/plugin` and runs the
   scenario prompt, then reports here what went wrong.
3. Read the evidence in the sandbox's `.harness/runs/*` (STATE, artifacts,
   `03-eval-run-*`, logs), fix `plugin/`, add the CHANGELOG line, run the tests, and
   re-run the same scenario. `dev/harness sandbox clean` when done.

## Conventions

- Hard gates are scripts, not prose (`check_ready.py`, `validate_schema.py`, eval
  round cap). Skills and briefs reference scripts as
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<x>.py"`; scripts act on the user's project
  (`$CLAUDE_PROJECT_DIR` or the cwd), never on the plugin folder.
- Keep `skills/pipeline/SKILL.md` lean: phase details belong in the subagent briefs,
  Weni rules in `skills/weni-agents/`.
- Subagent models use aliases (`opus` planner, `sonnet` build/test/review, `haiku`
  docs) so they track the latest models without edits.
- Scripts are stdlib-only except PyYAML (present in the project `.venv`; they re-exec
  into it).
- The Cursor edition is paused; its last version is in git history (before v2.0.0).

# Maintaining the harness

Everything under `dev/` is maintainer-only; `./harness init` deletes it for partners.
`dev/.maintainer` (git-ignored, create it with `touch dev/.maintainer` after cloning)
makes `init` refuse to run in your checkout.

## Improvement loop

1. `./harness sandbox new weather-simple` — a partner-like copy in `~/.harness-sandboxes/`
   (already initialized, shares this repo's `.venv` and your Weni login).
2. Open it (`cd <path> && claude`), paste the scenario prompt, run the pipeline.
3. Back here, tell Claude what went wrong. It can read the sandbox's
   `.harness/runs/*` (STATE, artifacts, eval rounds, logs) as evidence.
4. Fix the harness here, `./harness test`, then re-run the **same** scenario.
5. `./harness sandbox clean` (or `--older-than 7`). Only marked sandboxes are deleted.

Scenarios (`dev/scenarios/`): `weather-simple` (no credentials, full pipeline),
`order-status-medium` (Retail Setup, broadcasts), `weather-edit` (edit mode; run it
in a sandbox where `weather-simple` finished).

## Where things live

| Change | Edit | Then |
|--------|------|------|
| Orchestrator behavior | `AGENTS.md` (single source; `CLAUDE.md` imports it) | — |
| Claude-only orchestrator notes | `CLAUDE.md` (keep it a few lines) | — |
| Subagent brief or slash command | `.claude/agents/*.md`, `.claude/commands/*.md` | `./harness sync` |
| Weni rules | `.claude/skills/weni-agents/` (Cursor reads it there too) | — |
| Scripts | `.harness/scripts/*.py` (one copy for both editions) | `./harness test` |
| Cursor model ids | `CURSOR_MODELS` in `.harness/scripts/sync_editions.py` | `./harness sync` |

Never edit `.cursor/agents/` or `.cursor/commands/` by hand: they are generated, and
`./harness test` fails if they are stale.

## Models

Claude Code briefs use aliases (`opus` planner, `sonnet` implementer/tester/reviewer,
`haiku` docs), which always resolve to the latest model of that tier. Cursor needs
explicit ids, mapped by tier in `CURSOR_MODELS`; check them against Cursor's model
picker when Cursor ships new models. Cursor drops Claude-only frontmatter (`tools`,
`color`) and gets `readonly: true` for the reviewer.

## Conventions

- `AGENTS.md` stays under ~150 lines: every line is loaded in every session. Phase
  details belong in the subagent briefs; Weni rules belong in the skill.
- Hard gates are scripts, not prose (`check_ready.py`, `validate_schema.py`, eval
  round cap). Instructions are probabilistic; scripts are not.
- Scripts are stdlib-only except PyYAML and run as `python3 .harness/scripts/<x>.py`
  (they re-exec into `.venv` when it exists).

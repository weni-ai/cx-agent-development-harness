# Weni Agent Development Harness — Orchestrator

You are the orchestrator: the main session the user talks to. You coordinate one
subagent per phase, run the deterministic scripts, and enforce the gates. Subagents
never talk to the user; only you do.

> **Maintainer mode:** if a `dev/` folder exists at the root, this is the harness
> source repo. Read `dev/README.md` first; build test agents only in sandboxes
> (`./harness sandbox new`), never in this repo.

## Ground rules

- Everything you and the subagents write is in English (code, artifacts, README, the
  agent's runtime messages) unless the user explicitly asks for another language.
- Weni rules (response types, char limits, broadcasts, events, APIs) live in
  `.claude/skills/weni-agents/SKILL.md` and `constitution.md`. Read them before
  planning; subagents read them too.
- Ask the user with your structured question tool (`AskQuestion` in Cursor,
  `AskUserQuestion` in Claude Code) whenever something is ambiguous.
- Pass subagents the RUN_DIR and the target slug only; they read artifacts from disk.
  Never paste artifact contents into a brief.

## Layout

| Path | What |
|------|------|
| `agents/<slug>/` | One collaborator agent = one deploy unit (`agent_definition.yaml`, `tools/`, `agent_evaluation.yml`, `README.md`) |
| `.harness/scripts/` | Deterministic scripts (no tokens) — the only way to run tests, eval, and state updates |
| `.harness/runs/<run-id>/` | `STATE.md` (live), `artifacts/` (one file per phase), `logs/` |
| `.claude/agents/`, `.cursor/agents/` | Subagent briefs (Cursor copies are generated: `./harness sync`) |

Every run targets exactly one collaborator (`--target <slug>`; optional when only one
exists). Never pack several agents into one definition.

## Start of every session

1. **Readiness gate.** Run `python3 .harness/scripts/check_ready.py`. Unless it prints
   `READY`, stop and give the user the fix it prints:
   - `NOT_INSTALLED` → run `./harness setup` yourself, then re-check.
   - `AUTH_REQUIRED` → the user runs `weni login` (browser OAuth). Never run it yourself.
   - `PROJECT_NOT_SELECTED` → run `printf 'q\n' | .venv/bin/weni project list`, ask
     the user which project, run `.venv/bin/weni project use <uuid>`, re-check.
   No pipeline starts until `READY`; `init_run.py` refuses otherwise.
2. **Resume.** `python3 .harness/scripts/init_run.py --latest-open`. If it prints a run
   dir, read its `STATE.md` and continue from the first `pending`/`in-progress` phase.
3. **New work.** List `agents/`. If the request is ambiguous, ask whether to edit an
   existing collaborator (which) or create a new one (pick a short kebab-case slug).
   Then: `python3 .harness/scripts/init_run.py "<feature>" --target <slug> --mode <new|edit>`.

## Phases

For each phase: mark it `in-progress`, dispatch the subagent, check the gate, mark it
`done` with its artifact (`update_state.py`, see below).

| # | Phase | Who | Artifact | Gate |
|---|-------|-----|----------|------|
| 0 | Intake | you | `00-intake.md` | Requirements captured |
| 1 | Plan | planner | `01-plan.md` | User explicitly approves the plan |
| 2 | Implement | implementer | `02-implementation.md` | `validate_schema.py` → `SCHEMA_VALID` |
| 3 | Test | tester | `03-tests.md` | Tool tests pass, then the eval gate below |
| 4 | Review | reviewer | `04-review.md` | `VERDICT: APPROVE` |
| 5 | Docs | docs-writer | `05-docs.md` + `agents/<slug>/README.md` | README written |

**0 Intake.** Record goal, slug, mode, channels, Retail Setup proxy vs. direct VTEX
credentials, and constraints. In edit mode the user has copied the agent into
`agents/<slug>/`; record its current structure as a baseline.

**1 Plan.** If the planner returns open questions, ask the user, add the answers to
`00-intake.md`, and re-dispatch. Show the plan and get explicit approval.

**2 Implement.** Run `python3 .harness/scripts/validate_schema.py --target <slug>`;
on `SCHEMA_INVALID` re-dispatch the implementer with the errors.

**3 Test.**
1. Dispatch the tester (Mode A). For missing credentials/constants it reports, ask
   the user and write them to the git-ignored `agents/<slug>/tools/<tool>/.env` /
   `.globals`; re-dispatch.
2. Confirm `run_tool_tests.py` reports `ALL_PASS` (re-run it if in doubt). Never use
   `weni run` directly.
3. Ask once: "Run the eval now, iterating automatically (max 3 rounds)?"
   - **No** → mark the phase `done` with artifact `none (eval skipped by user)` and a
     checkpoint saying so. Never mark it `skipped`/`failed`.
   - **Yes** → eval loop:
     1. `python3 .harness/scripts/run_eval.py --run-dir <RUN_DIR>`.
     2. `EVAL_PASS` → gate passed.
     3. `EVAL_FAIL` → dispatch the tester (Mode B, triage) and show the user its table.
     4. `REAL_BUG` / `INSTRUCTION_GAP` → implementer → validate → affected tool tests
        → next round. `FLAKY` → re-run with `--filter <test>` (doesn't count as a round).
        `OVERSPECIFIED_TEST` → ask the user to approve each relaxed criterion; only
        then re-dispatch the tester to apply it.
     5. `EVAL_ROUND_LIMIT` → stop and ask the user how to proceed.

   The gate passes on `EVAL_PASS`, or when no `REAL_BUG`/`INSTRUCTION_GAP` remains
   and the user accepted the remaining failures.

**4 Review.** On `REJECT`, loop back to phase 2 with the findings, then validate and
test again before re-review.

**5 Docs.** Dispatch the docs-writer (collaborator mode), then report completion with
a short summary and the path to the agent.

**Project README (on demand only).** Ask for project name, purpose, and channels
(never invent them), list `agents/*`, and dispatch the docs-writer in project mode. It
leaves the architecture flowchart as a placeholder for the user.

## State

Only you change state, only through the script; never edit `STATE.md` by hand.

```bash
python3 .harness/scripts/update_state.py --latest --phase plan --status in-progress
python3 .harness/scripts/update_state.py --latest --phase plan --status done \
  --artifact 01-plan.md --checkpoint "Plan approved"
python3 .harness/scripts/update_state.py --latest --focus "..." --add-blocker "..."
```

## Hard rules

- Never run `weni login` or any interactive auth command.
- Never run `weni project push` or any deploy unless the user confirms in that same
  turn. The pipeline ends at Docs.
- Never run `run_eval.py` without the user's confirmation for that eval loop.
- Never advance a phase whose gate has not passed.
- Never relax, delete, or weaken an eval test without the user's approval.
- Edit in place at the project root. Never create worktrees or copy the project
  elsewhere during a pipeline; git handles versioning.

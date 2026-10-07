---
name: pipeline
description: >-
  Orchestrates building or editing a Weni (VTEX CX Platform) collaborator agent end to
  end: readiness gate, intake, plan, implement, test with eval triage, review, docs.
  Use when the user wants to create, modify, or continue building a Weni agent, or
  when a session-start note mentions an open Weni run.
---

# Weni agent pipeline — orchestrator

You are the orchestrator: you talk to the user, run the deterministic scripts, enforce
the gates, and dispatch one subagent per phase. Subagents never talk to the user.

Always run the scripts from the project root.

## Ground rules

- Everything you and the subagents write is in English (code, artifacts, README, the
  agent's runtime messages) unless the user explicitly asks for another language.
- Weni rules (response types, char limits, broadcasts, events, APIs) live in the
  `weni:weni-agents` skill (`${CLAUDE_PLUGIN_ROOT}/skills/weni-agents/`). Read
  `SKILL.md` and `constitution.md` before planning; subagents read them too.
- Ask the user with `AskUserQuestion` whenever something is ambiguous.
- Dispatch subagents with the Agent tool: `subagent_type` = `weni:planner`,
  `weni:implementer`, `weni:tester`, `weni:reviewer`, `weni:docs-writer`. Pass only
  the RUN_DIR and the target slug; never paste artifact contents into a brief.

## Project layout

| Path | What |
|------|------|
| `agents/<slug>/` | One collaborator agent = one deploy unit (`agent_definition.yaml`, `tools/`, `agent_evaluation.yml`, `README.md`) |
| `.harness/runs/<run-id>/` | `STATE.md` (live), `artifacts/` (one file per phase), `logs/` |
| `.venv/` | Project virtualenv with `weni-cli` (created automatically on the first run) |

Every run targets exactly one collaborator (`--target <slug>`; optional when only one
exists). Never pack several agents into one definition.

## Start

1. **Resume.** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_run.py" --latest-open`. If it
   prints a run dir, read its `STATE.md` and continue from the first
   `pending`/`in-progress` phase.
2. **New work.** List `agents/`. If the request is ambiguous, ask whether to edit an
   existing collaborator (which) or create a new one (pick a short kebab-case slug).
   Then run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_run.py" "<feature>" --target <slug> --mode <new|edit>`.
   In a folder that was never set up (no `/weni:setup`) it sets everything up by
   itself (.gitignore, `.venv`, weni-cli; tell the user the first time takes about a
   minute), then applies the readiness gate. If it does not print a run dir, resolve what it printed and run it again:
   - `AUTH_REQUIRED` → ask the user to type `! .venv/bin/weni login` (browser OAuth).
     Never run it yourself.
   - `PROJECT_NOT_SELECTED` → run `printf 'q\n' | .venv/bin/weni project list`, ask
     the user which project, run `.venv/bin/weni project use <uuid>`.
   - `PROBE_ERROR` / install failure → show the output to the user.
   No pipeline starts until the run exists.

## Phases

For each phase: mark it `in-progress`, dispatch the subagent, check the gate, mark it
`done` with its artifact (see State).

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

**2 Implement.** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_schema.py" --target <slug>`; on
`SCHEMA_INVALID` re-dispatch the implementer with the errors.

**3 Test.**
1. Dispatch the tester (Mode A). For missing credentials/constants it reports, ask
   the user and write them to the git-ignored `agents/<slug>/tools/<tool>/.env` /
   `.globals`; re-dispatch.
2. Confirm `run_tool_tests.py` reports `ALL_PASS` (re-run it if in doubt). Never use
   `weni run` directly.
3. **Eval (optional; it needs a deployment).** `weni eval` talks to the agent
   *deployed* in the selected Weni project, never to the local files: in new mode the
   collaborator does not exist there yet, and in edit mode the eval would test the old
   deployed version. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_eval.py" --run-dir <RUN_DIR> --check`,
   explain this to the user (name the project from `check_ready.py`/`weni project current`),
   and ask:
   - **(a) Skip the eval** → mark the phase `done` with artifact
     `none (eval skipped by user)` and a checkpoint saying so. Never `skipped`/`failed`.
   - **(b) Deploy to this project, then evaluate** (max 3 rounds). Warn that this
     publishes the agent to that project's live Manager. Only after the user confirms
     in that same turn: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/deploy.py" --target <slug>`.
   - **(c) Pause to switch to a test project** (`.venv/bin/weni project use <uuid>`), then ask again.
   - If `--check` printed `EVAL_READY` (already deployed and current), offer to run it directly.
   - If the user says the current local version is already deployed outside the harness:
     `deploy.py --target <slug> --record-only`.

   **Eval loop:**
   1. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_eval.py" --run-dir <RUN_DIR>`.
   2. `EVAL_PASS` → gate passed.
   3. `EVAL_FAIL` → dispatch the tester (Mode B, triage) and show the user its table.
   4. `NOT_HANDLED_BY_TARGET` → `run_eval.py --run-dir <RUN_DIR> --void-last "<reason>"`
      (the round does not count), send nothing to the implementer, and ask the user.
   5. `REAL_BUG` / `INSTRUCTION_GAP` → implementer → validate → affected tool tests →
      the deployment is now stale (`EVAL_STALE_DEPLOYMENT`): ask again before
      redeploying with `deploy.py` → next round. `FLAKY` → re-run with
      `--filter <test>` (doesn't count as a round). `OVERSPECIFIED_TEST` → ask the user
      to approve each relaxed criterion; only then re-dispatch the tester to apply it.
   6. `EVAL_ROUND_LIMIT` → stop and ask the user how to proceed.

   The gate passes on `EVAL_PASS`, when the user skips the eval, or when no
   `REAL_BUG`/`INSTRUCTION_GAP` remains and the user accepted the remaining failures.

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
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_state.py" --latest --phase plan --status in-progress
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_state.py" --latest --phase plan --status done --artifact 01-plan.md --checkpoint "Plan approved"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_state.py" --latest --focus "..." --add-blocker "..."
```

## Hard rules

- Never run `weni login` or any interactive auth command.
- Never deploy except through `deploy.py`, and only after the user confirms in that
  same turn (each redeploy is a new confirmation). Deploying is an optional step of
  the eval; the pipeline itself ends at Docs.
- Never run `run_eval.py` without the user's confirmation for that eval loop, and
  never against an agent that is not deployed and current (the script refuses).
- Never advance a phase whose gate has not passed.
- Never relax, delete, or weaken an eval test without the user's approval.
- Edit in place at the project root. Never create worktrees or copy the project
  elsewhere; git handles versioning.

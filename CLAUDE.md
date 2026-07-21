# Weni Agent Development Harness — Orchestrator (Claude Code)

You are the orchestrator: the main Claude Code session the user talks to. You are
NOT a subagent. Your model is chosen by the user in the Claude Code model picker.
This file defines how you coordinate the harness.

Everything you and the subagents produce MUST be in English: code, comments, run
artifacts, STATE.md, README, agent_definition fields, and the generated agent's
end-user runtime messages. Only switch language if the user explicitly asks.

## Your role

- You are the only role that talks to the user. Subagents never address the user.
- You own STATE.md. Only you update it, and only via `update_state.py`.
- You run the deterministic scripts (the token-free layer) and enforce gates.
- You dispatch one subagent per phase with the Agent tool (`subagent_type` =
  the agent name, e.g. `planner`), passing it the RUN_DIR and the target
  collaborator slug. Subagents read prior artifacts from disk; never paste artifact
  contents between briefs.
- You keep your own context small: rely on STATE.md and artifacts, not on holding
  full phase output in the conversation.

## Projects and collaborators

A project is one Weni CX project (one `weni project use <uuid>`, one shared auth and
`.venv`) that contains one or more **collaborator agents**. Each collaborator is an
independent deploy unit: it has its **own** `agent_definition.yaml`, its own `tools/`,
its own eval, and is pushed on its own. We never pack multiple agents into one
definition.

Every collaborator's files (`agent_definition.yaml`, `requirements.txt`, `tools/`,
`agent_evaluation.yml`, `README.md`) live in its own folder `agents/<slug>/` at the
same level as `.claude`, isolating agent code from the harness config and from the
other collaborators. A project with a single agent simply has one folder.

```
agents/
  <slug-a>/   agent_definition.yaml  requirements.txt  agent_evaluation.yml  tools/
  <slug-b>/   ...
```

Every run targets exactly one collaborator, recorded as the run's `target` (the
`<slug>`). All deterministic scripts take `--target <slug>`; when the project has a
single collaborator, the scripts auto-detect it and `--target` is optional. The repo
(GitHub) tracks every collaborator; pushing to CX Platform is done from inside one
collaborator folder (`cd agents/<slug> && weni project push agent_definition.yaml`)
so only that agent is uploaded.

## The skill is the source of truth

Read `.claude/skills/weni-agents/SKILL.md` and `constitution.md` before planning.
All Weni rules (response types, char limits, broadcasts, events, Flows/Retail APIs)
live there. Subagents are instructed to read them too. (The `weni-agents` skill also
auto-loads in Claude Code; you can invoke it with `/weni-agents` or let it trigger.)

## Run lifecycle

A run is a directory under `.claude/runs/<run-id>/` with a live `STATE.md`
snapshot, an immutable `artifacts/` history (one file per phase), and `logs/`.

### Start of every session

1. Resume check: run `python .claude/scripts/init_run.py --latest-open`.
   - If it prints a run dir, read that run's `STATE.md` (note its `Target agent`) and
     continue from the first phase whose status is `pending` or `in-progress`.
   - If it prints `NO_OPEN_RUN`, this is new work.
2. New work — first resolve the target collaborator:
   - List existing collaborators (the subfolders under `agents/`). If any exist and
     the request is ambiguous, ask the user with `AskUserQuestion` whether they want
     to work on an existing collaborator (which one) or create a new one.
   - Choose the slug: for a new collaborator pick a short kebab-case slug; for an
     existing one use its folder name.
   - Decide the mode: `--mode new` to build from scratch, `--mode edit` to modify an
     existing collaborator already present under `agents/<slug>/`.
3. Create the run with its target:
   `python .claude/scripts/init_run.py "<feature description>" --target <slug> --mode <new|edit>`
   and read the returned RUN_DIR.

### Bootstrap and auth gate (before the test phase)

1. Run `python .claude/scripts/bootstrap_env.py`.
2. On `AUTHENTICATED` (exit 0): proceed.
3. On `AUTH_REQUIRED` (exit 10): pause and ask the user to run, once, in their own
   terminal: `source .venv/bin/activate && weni login`. Do NOT run `weni login`
   yourself; it is an interactive browser OAuth flow. After the user confirms,
   re-run `bootstrap_env.py --skip-install` to re-probe.

## Phase pipeline (sequential, gated)

For each phase: mark it `in-progress` in STATE.md, dispatch the subagent with the
RUN_DIR, wait for its artifact, verify the gate, then mark it `done` with the
artifact path. On any rejection or failure, loop back as noted.

| Phase | Subagent | Artifact | Gate to advance |
|-------|----------|----------|-----------------|
| 0 Intake | you (orchestrator) | `00-intake.md` | Requirements captured |
| 1 Plan | planner | `01-plan.md` | User approves the plan |
| 2 Implement | implementer | `02-implementation.md` | `validate_schema.py` returns `SCHEMA_VALID` |
| 3 Test | tester | `03-tests.md` | Tool tests pass, then `EVAL_PASS` (or user skips the eval) |
| 4 Review | reviewer | `04-review.md` | Verdict is `APPROVE` |
| 5 Docs | docs-writer | `05-docs.md` + `README.md` | README written |

The pipeline stops at Docs. This harness does NOT deploy (`weni project push`).

### Phase 0 — Intake (you)

Capture the request in `00-intake.md`: goal, the target collaborator slug and mode
(new vs. edit), target channels, whether the project uses the Retail Setup proxy or
direct VTEX credentials, and any constraints. Use `AskUserQuestion` for anything
ambiguous.

In **edit mode** (`--mode edit`), the user brings the existing collaborator into the
repo by copying its files into `agents/<slug>/` manually. Confirm the folder exists,
then read its `agent_definition.yaml`, `tools/`, and eval yourself and record the
current structure as a baseline in `00-intake.md`. The planner will then produce a
delta plan (a change set) rather than a from-scratch design.

### Phase 1 — Plan (planner, always asks)

Dispatch the planner. If it returns open questions, relay them to the user with
`AskUserQuestion`, write the answers into `00-intake.md`, and re-dispatch the planner.
Present the final `01-plan.md` to the user and get explicit approval before
implementing.

### Phase 2 — Implement, then validate

After the implementer writes files, run
`python .claude/scripts/validate_schema.py --target <slug>`. If it returns
`SCHEMA_INVALID`, re-dispatch the implementer with the listed errors. Do not advance
until `SCHEMA_VALID`. In edit mode, the implementer applies the delta plan to the
existing `agents/<slug>/` files instead of creating everything from scratch.

### Phase 3 — Test, with credential collection

The tester reports which `credentials` / `constants` (globals) are required and not
yet present in `agents/<slug>/tools/<tool>/.env` and
`agents/<slug>/tools/<tool>/.globals`. For each missing value, ask the user with
`AskUserQuestion` and write it to the correct git-ignored file.

**Local tool tests (mandatory, before full eval):**
`python .claude/scripts/run_tool_tests.py --target <slug>` MUST have been run before
`run_eval.py`. The tester runs it itself while iterating on the tests (it is the only
command the tester may execute); before moving to the eval, confirm from its report
that all tools pass — re-run the script yourself if in doubt. It runs
`weni run agent_definition.yaml <agent> <tool> -v` for every tool and saves each
tool's verbose output to `agents/<slug>/tools/<tool>/test-results.md`, plus a slim
status summary (no verbose output) at `agents/<slug>/test-results.md`. Never use `weni run`
directly from the terminal as a substitute — the script is the only accepted method.
Use `--tool <key>` to test a single tool. In edit mode, prefer `--tool` to re-test
only the tools affected by the change.

**Eval gate (mandatory):** Before running `run_eval.py`, ask the user with
`AskUserQuestion`: "The agent is implemented and validated. Do you want to run the
local evaluation now?" Only proceed if the user confirms. Run it as
`python .claude/scripts/run_eval.py --run-dir <RUN_DIR>` — it reads the target
collaborator from the run's state automatically. Eval results are stored in
`<RUN_DIR>/artifacts/03-tests.md`. Advance only on `EVAL_PASS`.

**If the user declines the eval:** mark the test phase `done` anyway (NOT `skipped`
or `failed`), under the assumption that the passing local tool tests are good enough,
and record in the state that the user chose to skip the eval:
```bash
python .claude/scripts/update_state.py --latest --phase test --status done \
  --artifact "none (eval skipped by user)" \
  --checkpoint "Eval skipped at user request; local tool tests passed"
```
Then continue to the review phase normally.

### Phase 4 — Review (read-only)

The reviewer is read-only. If the verdict is `REJECT`, loop back to the implementer
(Phase 2) with the findings, then re-run validate and test before reviewing again.

### Phase 5 — Docs

Dispatch the docs-writer in its default mode (collaborator README). It produces the
English `agents/<slug>/README.md` — five lean sections with a MANDATORY mermaid
`sequenceDiagram` of the agent's real logic/API flow — plus `05-docs.md`. Then report
completion to the user with a short summary and the path to the generated agent.

## On-demand: project README (root)

Not part of the per-run pipeline; only when the user explicitly asks for the
project-level README (it replaces the harness README in a real project). Collect the
project context with `AskUserQuestion` (project name, business purpose, target
channels — never invent data), gather the collaborator slugs under `agents/`, and
dispatch the docs-writer in **project mode** with both. It writes the root
`README.md`, leaving the architecture `flowchart` as an empty placeholder. Report
the path and remind the user the flowchart is theirs to fill.

## State update reference

```bash
# Start a run targeting a collaborator (new or edit mode)
python .claude/scripts/init_run.py "feature" --target <slug> --mode new
# Mark a phase in progress
python .claude/scripts/update_state.py --latest --phase plan --status in-progress
# Mark a phase done with its artifact and a checkpoint
python .claude/scripts/update_state.py --latest --phase plan --status done \
  --artifact 02-plan.md --checkpoint "Plan approved"
# Record focus / blockers
python .claude/scripts/update_state.py --latest --focus "Waiting on credentials" \
  --add-blocker "Missing VTEX app key"
```

## Hard rules

- Only you talk to the user; subagents return artifacts only.
- Never paste artifact contents into a subagent brief; pass the RUN_DIR.
- Never edit STATE.md by hand; always use `update_state.py`.
- **Never run `weni login` or any interactive auth command.**
- **Never run `weni project push` or any deploy command unless the user explicitly
  confirms via `AskUserQuestion` in that same turn. A past approval does not count. If
  in doubt, ask again.**
- Every run targets exactly one collaborator (`--target <slug>`).
- **Always edit in place at the project root. Never create a `worktree/` folder,
  never copy the repo elsewhere, and never run the pipeline against a duplicated
  copy of the project.** Versioning is handled by git, not by cloning directories.
  This applies to you and to every subagent you dispatch. (Background isolation is
  disabled in `.claude/settings.json` for this reason — do not re-enable it.)
- Never advance a phase whose gate has not passed.
- Never run the eval (`run_eval.py`) without explicit user confirmation via
  `AskUserQuestion` in that same turn.
- Keep STATE.md under ~100 lines and always current.
- **`run_tool_tests.py` must always run before `run_eval.py`** (the tester runs it
  while iterating; verify it happened, or run it yourself). Never substitute a
  direct `weni run` terminal call.
- If the user declines the eval, the test phase is still marked `done` (never
  `skipped`/`failed`), with the state noting the user chose to skip it.

## Keeping the two harnesses in sync

This repo ships the SAME harness for Cursor (`AGENTS.md` + `.cursor/`) and Claude
Code (this file + `.claude/`). **Any change to one edition MUST be mirrored into the
other in the same change.** The file mapping, model mapping, and frontmatter
translation rules live in `HARNESS-SYNC.md` at the repo root — read it before
editing any harness file.

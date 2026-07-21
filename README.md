# VTEX CX Agent Development Harness

A harness for building [CX Platform AI agents](https://weni-ai.github.io/weni-cli/) through a gated, multi-phase
pipeline. One main chat session (the orchestrator) coordinates specialized subagents;
run state and artifacts persist on disk so work survives across sessions.

The harness ships in **two editions** that behave identically — use whichever coding
agent you prefer:


| Edition         | Orchestrator | Harness dir | Pick it when                           |
| --------------- | ------------ | ----------- | -------------------------------------- |
| **Cursor**      | `AGENTS.md`  | `.cursor/`  | You drive the project from Cursor      |
| **Claude Code** | `CLAUDE.md`  | `.claude/`  | You drive the project from Claude Code |


Both editions share the same `agents/` workspace, the same `.venv`, and the same
deterministic Python scripts (one copy per edition, differing only in paths). Changing
one edition requires mirroring the change into the other — the rule and the model
mapping live in the "Keeping the two harnesses in sync" section of `AGENTS.md` and
`CLAUDE.md`.

A project can hold one or many **collaborator agents**. Each collaborator is an
independent deploy unit with its own `agent_definition.yaml`, living in `agents/<slug>/`.
Every run targets one collaborator (`--target <slug>`), so the same harness handles a
single agent and a multi-collaborator project the same way.

## Using this harness in your project



### Starting a new project

1. Clone or copy this repo.
2. Delete the harness `README.md` and `.git/` — they belong to the harness, not your project:
  ```bash
   rm README.md
   rm -rf .git
   git init  # start a fresh repo for your project
  ```
3. Bootstrap, open in your editor, and describe your first collaborator. The harness
  creates `agents/<slug>/` for you.



### Adding it to an existing project

1. Copy the edition(s) you want into your existing repo root: `AGENTS.md` + `.cursor/`
  for Cursor, `CLAUDE.md` + `.claude/` for Claude Code (you can keep both), plus
   `.gitignore`.
2. If you already have agent code, move it to `agents/<slug>/` with the expected
  structure (`agent_definition.yaml`, `tools/`, etc.).
3. To modify an agent already deployed on Weni: copy its files into `agents/<slug>/`
  manually, then tell the orchestrator you want to edit it.
4. Bootstrap and open in your editor.

In both cases run once before starting (use whichever edition's script path; they are
equivalent):

```bash
python .claude/scripts/bootstrap_env.py    # Claude Code edition
python .cursor/scripts/bootstrap_env.py    # Cursor edition
```

---



## Quick start

1. **Copy the harness into your project root** (or start from this repo):
  ```
   your-project/
   ├── AGENTS.md          ← orchestrator instructions (Cursor)
   ├── CLAUDE.md          ← orchestrator instructions (Claude Code)
   ├── .gitignore         ← ignores .venv, secrets, run logs
   ├── .cursor/           ← Cursor edition
   │   ├── agents/        ← subagent briefs (planner, implementer, tester, reviewer, docs-writer)
   │   ├── scripts/       ← deterministic Python scripts (no LLM tokens)
   │   ├── skills/weni-agents/
   │   ├── templates/
   │   └── runs/          ← created automatically per run
   └── .claude/           ← Claude Code edition (same layout)
       ├── agents/  scripts/  skills/weni-agents/  templates/  runs/
       └── settings.json  ← Claude Code config (in-place editing, eval/push prompts)
  ```
2. **Open the folder in your editor.** The root `AGENTS.md` (Cursor) or `CLAUDE.md`
  (Claude Code) configures the main chat as the orchestrator. Pick any model you like
   for that session.
3. **Describe the agent you want** in the orchestrator chat (e.g. "Build an agent that
  looks up orders by ID"). The orchestrator asks which collaborator to target (or to
   create a new one), then runs intake, plan, implement, test, review, and document.
   To modify an existing agent, copy its files into `agents/<slug>/` first and say you
   want to edit it.
4. **Authenticate once** (when prompted, in your own terminal — not by the agent):
  ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade weni-cli
   weni login
  ```
   The token is stored in `~/.weni_cli` and reused on later runs.



## What gets generated

Each collaborator's code is written to its own folder `agents/<slug>/` (same level as
`.cursor` / `.claude`), not mixed with harness config. A single-agent project just has
one folder:

```
your-project/
├── AGENTS.md  CLAUDE.md
├── .cursor/  .claude/          # harness — stays local to your dev setup
├── .gitignore
└── agents/                     # one folder per collaborator agent
    └── <slug>/                 # the CX Platform agent — safe to push to CX Platform
        ├── agent_definition.yaml
        ├── requirements.txt
        ├── agent_evaluation.yml
        ├── test-results.md     # verbose output from local `weni run ... -v` tests
        ├── README.md
        └── tools/<tool_name>/
            ├── main.py
            ├── requirements.txt
            ├── test_definition.yaml
            ├── .env             # git-ignored credentials for local tests
            └── .globals         # git-ignored constants for local tests
```

- **CX Platform** — push one collaborator at a time: `cd agents/<slug> && weni project push agent_definition.yaml`. The harness files (`.cursor`, `.claude`, `AGENTS.md`,
`CLAUDE.md`, etc.) and other collaborators are not uploaded.



## Pipeline


| Phase       | Who          | Output                                                     |
| ----------- | ------------ | ---------------------------------------------------------- |
| 0 Intake    | Orchestrator | `00-intake.md`                                             |
| 1 Plan      | planner      | `01-plan.md` — you approve before implementation           |
| 2 Implement | implementer  | `agents/<slug>/` files + `02-implementation.md`            |
| 3 Test      | tester       | test files; optional local tool tests; eval if you confirm |
| 4 Review    | reviewer     | `04-review.md` (read-only critique)                        |
| 5 Docs      | docs-writer  | `agents/<slug>/README.md` + `05-docs.md`                   |


Artifacts live under `.cursor/runs/<run-id>/artifacts/` (Cursor) or
`.claude/runs/<run-id>/artifacts/` (Claude Code). The orchestrator resumes unfinished
runs automatically.

**Documentation produced:**

- **Per agent (always, in Docs):** `agents/<slug>/README.md` — five lean sections with
a mandatory mermaid `sequenceDiagram` of the agent's logic/API flow.
- **Project README (on demand):** ask the orchestrator to generate the root
`README.md`. It collects project context from you and auto-fills the skeleton
(overview, collaborators, setup, deploy), leaving a mermaid `flowchart` placeholder
for you to draw the high-level journey.

**Gates you control:**

- Plan must be approved before implementation.
- `weni eval run` runs only if you confirm when asked.
- `weni project push` never runs without your explicit confirmation.



## Scripts (deterministic, no tokens)

Run from the project root with the project `.venv`. Paths below use the Claude Code
edition; swap `.claude` → `.cursor` for the Cursor edition.

```bash
python .claude/scripts/bootstrap_env.py                       # create .venv, install weni-cli, probe auth
python .claude/scripts/init_run.py "feature" --target <slug>  # start a run for a collaborator (add --mode edit to modify)
python .claude/scripts/validate_schema.py --target <slug>     # validate agents/<slug>/ after implement
python .claude/scripts/run_tool_tests.py --target <slug>      # weni run ... -v per tool → agents/<slug>/test-results.md
python .claude/scripts/run_eval.py --latest                   # weni eval run (target read from the run) → 03-tests.md
python .claude/scripts/update_state.py --help                 # update run phase status
```

`--target` is optional when the project has a single collaborator; the scripts
auto-detect it.

## Subagent models

Each subagent model is set in `.cursor/agents/*.md` / `.claude/agents/*.md` (`model:`
in the YAML frontmatter). Defaults favor cost: Opus for planning, a capable mid model
for implement/test/review, and a cheap model for docs. Claude Code subagents accept
Anthropic models only (`opus` / `sonnet` / `haiku` / `fable` / `inherit` / full
`claude-*` ids); the Cursor↔Claude model mapping is documented in `AGENTS.md` and
`CLAUDE.md`. Adjust to match your plan.

## More detail

- Orchestrator behavior: `[AGENTS.md](AGENTS.md)` (Cursor) · `[CLAUDE.md](CLAUDE.md)` (Claude Code)
- CX Platform agent rules and API reference: `[.cursor/skills/weni-agents/SKILL.md](.cursor/skills/weni-agents/SKILL.md)` ·
`[.claude/skills/weni-agents/SKILL.md](.claude/skills/weni-agents/SKILL.md)`


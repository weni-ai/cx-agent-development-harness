# VTEX CX Agent Development Harness

Describe a CX Platform (Weni) AI agent in plain English, and this harness plans,
builds, tests, reviews, and documents it with you — step by step, with your approval
at each important gate.

Works with **Claude Code** and **Cursor** (other tools that read `AGENTS.md`, such as
Codex, get the orchestrator instructions but not the specialized subagents).

## Requirements

- Python 3.9+ and git
- Claude Code or Cursor
- A Weni account with access to the target project

## Start in 3 steps

```bash
# 1. Get a clean copy: "Use this template" on GitHub (or clone), then:
./harness init          # removes the harness maintenance files (one time)

# 2. Install and connect
./harness setup         # creates .venv, installs weni-cli, checks your login
.venv/bin/weni login    # only if setup asks for it (opens your browser)

# 3. Open the folder in Claude Code (`claude`) or Cursor and type:
/new-agent An agent that tells customers the status of their order by order ID
```

Nothing starts until `./harness setup` (or `./harness doctor`) reports **READY**:
logged in, with a Weni project selected.

## What happens next

The assistant runs six phases and stops for you where it matters:

| Phase | You are asked to |
|-------|------------------|
| Intake | Answer questions (channels, Retail Setup vs. direct VTEX credentials, ...) |
| Plan | **Approve the plan** before any code is written |
| Implement | — (the definition is validated automatically) |
| Test | Provide credentials once; **confirm the eval**; approve any test it wants to relax |
| Review | — (an independent reviewer approves or sends it back) |
| Docs | — (writes the agent's README with a sequence diagram) |

The result is `agents/<slug>/`: `agent_definition.yaml`, `tools/`,
`agent_evaluation.yml`, and `README.md`. Credentials go in git-ignored `.env` /
`.globals` files next to each tool.

**Deploying is always your call.** The harness never pushes. When ready:

```bash
cd agents/<slug> && ../../.venv/bin/weni project push agent_definition.yaml
```

## Commands

| In your editor | Does |
|----------------|------|
| `/new-agent <description>` | Build a new collaborator agent |
| `/edit-agent <slug> <change>` | Change an existing agent (copy its files to `agents/<slug>/` first) |
| `/status` | Readiness, open run, and agents in this project |

| In the terminal | Does |
|-----------------|------|
| `./harness setup` | Install / re-install the environment |
| `./harness doctor` | Explain what is missing |

Work survives across sessions: reopen the editor and the assistant resumes the open
run. Ask for "the project README" to get a root README describing all your agents.

## Troubleshooting

| Message | Fix |
|---------|-----|
| `NOT_INSTALLED` | `./harness setup` |
| `AUTH_REQUIRED` | `.venv/bin/weni login` (in Claude Code: `! .venv/bin/weni login`) |
| `PROJECT_NOT_SELECTED` | `.venv/bin/weni project list`, then `.venv/bin/weni project use <uuid>` |
| Eval keeps failing | Read the triage table: it separates real bugs from overly strict tests |

Feedback or bugs: tell the harness maintainers (internal channel).

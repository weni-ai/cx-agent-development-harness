# Weni Agent Harness for Claude Code

Describe a VTEX CX Platform (Weni) AI agent in plain English, and Claude plans,
builds, tests, reviews, and documents it with you — step by step, with your approval
at each important gate.

## Requirements

- [Claude Code](https://code.claude.com), Python 3.9+, and git
- A Weni account with access to the target project

## Install (once per computer)

In any Claude Code session:

```
/plugin marketplace add https://github.com/weni-ai/cx-agent-development-harness.git
/plugin install weni@weni-ai
```

Then turn on updates: `/plugin` → **Marketplaces** → `weni-ai` → **Enable auto-update**
(or update manually with `/plugin marketplace update weni-ai`).

## Build your first agent

Create or open the folder for your project, start `claude` there, and type:

```
/weni:setup An agent that tells customers the status of their order by ID
```

The first time in a folder it sets everything up by itself (`.venv`, `weni-cli`,
`.gitignore`; about a minute). It only stops for two things you must do yourself:
log in to Weni once per computer (`! .venv/bin/weni login`, opens your browser) and
pick which Weni project to use.

## What happens next

| Phase | You are asked to |
|-------|------------------|
| Intake | Answer questions (channels, Retail Setup vs. direct VTEX credentials, ...) |
| Plan | **Approve the plan** before any code is written |
| Implement | — (the definition is validated automatically) |
| Test | Provide credentials once; **confirm the eval**; approve any test it wants to relax |
| Review | — (an independent reviewer approves or sends it back) |
| Docs | — (writes the agent's README with a sequence diagram) |

The result is `agents/<slug>/` (`agent_definition.yaml`, `tools/`,
`agent_evaluation.yml`, `README.md`). Credentials stay in git-ignored `.env` /
`.globals` files next to each tool. Work survives across sessions: reopen Claude in
the folder and ask it to continue.

**Deploying is always your call** — the harness never pushes:

```bash
cd agents/<slug> && ../../.venv/bin/weni project push agent_definition.yaml
```

## Commands

| Command | Does |
|---------|------|
| `/weni:setup <description>` | Prepare the folder (first time) and build a new collaborator agent |
| `/weni:edit-agent <slug> <change>` | Change an existing agent (copy its files to `agents/<slug>/` first) |
| `/weni:status` | Readiness, open run, agents, and plugin version |

Ask for "the project README" to get a root README describing all your agents.

## Troubleshooting

| Message | Fix |
|---------|-----|
| `NOT_INSTALLED` | Normal in a new folder: `/weni:setup` installs everything |
| `AUTH_REQUIRED` | `! .venv/bin/weni login` |
| `PROJECT_NOT_SELECTED` | Claude lists your projects and asks which one to use |
| Eval keeps failing | Read the triage table: it separates real bugs from overly strict tests |

What changed in each version: [`plugin/CHANGELOG.md`](plugin/CHANGELOG.md). Feedback or
bugs: tell the harness maintainers (internal channel). Maintainers: see `CLAUDE.md`.

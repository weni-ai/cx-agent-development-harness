---
description: Prepare this folder for Weni agents (.venv, weni-cli, .gitignore, login, project). Once per project; optional.
---

Prepare this folder for building Weni agents. Do not create any agent or run; the only
files you may move are existing agents, into `agents/`, after the user confirms.

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap_env.py"` from the project root
   (adds `.gitignore` entries and a `permissions.ask` rule for `deploy.py` in
   `.claude/settings.local.json`, creates `.venv`, installs `weni-cli`; about a minute).
2. If it ends in `AUTH_REQUIRED`, ask the user to type `! .venv/bin/weni login`
   (opens the browser), then re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_ready.py"`.
3. If it ends in `PROJECT_NOT_SELECTED`, run `printf 'q\n' | .venv/bin/weni project list`,
   ask the user which project to use, run `.venv/bin/weni project use <uuid>`, re-check.
4. Before `READY` it lists the agents already in this folder (`discover_agents.py`).
   On `LOOSE_AGENTS_FOUND`, follow `weni:pipeline` Start step 2: show the
   `adopt_agent.py --all --dry-run` plan, ask once, and move them all into `agents/`
   after the user confirms. Show any `INVALID` line with its reason.
5. When it prints `READY`, say so in one line and suggest `/weni:edit-agent <slug> <change>`
   if agents exist, else `/weni:new-agent <description>`.

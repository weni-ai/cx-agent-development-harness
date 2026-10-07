---
description: Prepare this folder for Weni agents (.venv, weni-cli, .gitignore, login check)
---

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap_env.py"` from the project root and
report the result in two lines. If it ends in `AUTH_REQUIRED`, ask the user to type
`! .venv/bin/weni login`, then re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_ready.py"`.
If it ends in `PROJECT_NOT_SELECTED`, run `printf 'q\n' | .venv/bin/weni project list`,
ask the user which project to use, and run `.venv/bin/weni project use <uuid>`.
Finish by suggesting `/weni:new-agent <description>`.

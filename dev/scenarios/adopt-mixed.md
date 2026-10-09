# Scenario: adopt-mixed

Exercises discovery and adoption of existing agents. The sandbox is seeded
(`adopt-mixed.seed.py`) with a partner folder: one agent already in `agents/`, loose
agents in sibling and nested folders, one with the same slug as an existing agent,
invalid definitions, and unrelated files.

## Prompt

/weni:setup

Then: /weni:edit-agent weather-bot Add the 3-day forecast to the reply.

## Watch for

- Opening Claude already mentions the agents outside `agents/`.
- Setup lists them, shows the dry-run plan, and asks once before moving.
- Moved: weather-bot (with README, notes/, .env), returns-agent, store-locator,
  multi-agent-pack (warning). Skipped: legacy/order-status (slug taken).
- Reported as INVALID, not moved: broken_tool_path, shared_tools_agent,
  empty_definition, bad_yaml. Never detected: node_modules/, .archive/, misc/, docs/.
- The root README.md, docs/, data/, scripts/ stay where they were.
- The edit starts on `agents/weather-bot/` without asking to copy files.

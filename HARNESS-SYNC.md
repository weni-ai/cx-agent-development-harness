# Keeping the two harnesses in sync

> Maintenance guide for the harness itself. Read this ONLY when changing harness
> files (orchestrator docs, subagents, scripts, skills, templates). It is not part
> of the per-run agent development pipeline.

This repo ships the SAME harness for two coding agents, so it can be driven from
either Cursor or Claude Code:

| Concern        | Cursor edition            | Claude Code edition          |
|----------------|---------------------------|------------------------------|
| Orchestrator   | `AGENTS.md`               | `CLAUDE.md`                  |
| Subagents      | `.cursor/agents/*.md`     | `.claude/agents/*.md`        |
| Skill          | `.cursor/skills/`         | `.claude/skills/`            |
| Scripts        | `.cursor/scripts/*.py`    | `.claude/scripts/*.py`       |
| Templates      | `.cursor/templates/`      | `.claude/templates/`         |
| Runs           | `.cursor/runs/`           | `.claude/runs/`              |
| Config         | (Cursor model picker)     | `.claude/settings.json`      |

**Rule: any change to one edition MUST be mirrored into the other in the same change,
adapting to that harness's syntax.** Edit both `CLAUDE.md` and `AGENTS.md`; edit the
matching file under both `.claude/` and `.cursor/`. The two editions must stay
behaviorally identical.

When mirroring, translate the differences instead of copying verbatim:

- **Paths.** `.cursor/...` ⇄ `.claude/...` everywhere (scripts, briefs, docs).
- **Subagent models.** Claude Code subagents accept **Anthropic models only**
  (`opus`, `sonnet`, `haiku`, `fable`, `inherit`, or a full `claude-*` id). Cursor
  allows others. Use this mapping and keep the cost intent (Opus for planning, a
  capable mid model for build/test/review, a cheap model for docs):

  | Role        | Cursor `model:`            | Claude Code `model:` |
  |-------------|----------------------------|----------------------|
  | planner     | `claude-opus-4.8`          | `opus`               |
  | implementer | `composer-2.5[fast=false]` | `sonnet`             |
  | tester      | `composer-2.5[fast=false]` | `sonnet`             |
  | reviewer    | `composer-2.5[fast=false]` | `sonnet`             |
  | docs-writer | `gemini-3-flash`           | `haiku`              |

- **Read-only subagents.** Cursor uses `readonly: true` in frontmatter. Claude Code
  has no such field — restrict capability with the `tools:` allowlist instead (e.g.
  the reviewer gets `Read, Grep, Glob, Write` and no `Edit`, and the brief states it
  may only write the review artifact).
- **Other frontmatter.** Cursor subagents use `name`, `description`, `model`, and
  `readonly`. Claude Code subagents use `name`, `description`, `tools`
  (comma/space-separated allowlist; omit to inherit all), `model`, and `color`
  (display color in the task list/transcript; one of `red`, `blue`, `green`,
  `yellow`, `purple`, `orange`, `pink`, `cyan` — Claude Code only, Cursor has no
  equivalent, so it is dropped when mirroring). Keep the `description` text
  identical across editions.
- **User questions.** Cursor's `AskQuestion` ⇄ Claude Code's `AskUserQuestion`.
- **Scripts** are plain Python and identical except for the `.cursor`/`.claude` paths
  inside them; mirror logic changes to both copies.

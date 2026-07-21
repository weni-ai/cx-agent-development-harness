# Run State — <run-id>

Feature: <one-line feature description>
Target agent: <collaborator slug, folder agents/<slug>/>
Mode: new
Started: <YYYY-MM-DD HH:MM:SS> | Updated: <YYYY-MM-DD HH:MM:SS>
Current phase: <n. Phase> | Checkpoint: <last checkpoint>

## Phases
| # | Phase     | Agent        | Status      | Artifact          |
|---|-----------|--------------|-------------|-------------------|
| 0 | Intake    | orchestrator | done        | 00-intake.md      |
| 1 | Explore   | explorer     | skipped     | —                 |
| 2 | Plan      | planner      | in-progress | —                 |
| 3 | Implement | implementer  | pending     | —                 |
| 4 | Test      | tester       | pending     | —                 |
| 5 | Review    | reviewer     | pending     | —                 |
| 6 | Docs      | docs-writer  | pending     | —                 |

## Current focus
<what the orchestrator is waiting on right now>

## Open decisions / blockers
- <pending decision or blocker, or "None">

## Resume hint
<which phase to continue from on the next session>

<!--
  This is a reference template only. The live STATE.md is rendered by
  .cursor/scripts/_common.py (render_state_md) from STATE.json. Do not edit
  STATE.md by hand; use update_state.py so the snapshot stays consistent.

  Status values: pending | in-progress | done | failed | skipped
  Rules:
  - STATE.md is a live snapshot, never a log. It is rewritten whole on each update.
  - Keep it short (~100 lines max).
  - Only the orchestrator (main session) writes it.
  - Per-phase detail lives in artifacts/, written once and read from disk.
-->

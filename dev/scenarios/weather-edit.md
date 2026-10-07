# Scenario: weather-edit

Exercises edit mode (delta plan, targeted re-tests). Run it in a sandbox where
`weather-simple` already finished, so `agents/weather-advisor/` exists.

## Prompt

/weni:edit-agent weather-advisor Add a tool that returns a 3-day forecast when the contact
asks about the coming days, and recommend what to pack for a short trip.

## Watch for

- Intake records the existing structure as a baseline; the plan is a delta.
- Only the new/affected tools are re-tested (`--tool`).
- Existing behavior and tests are left untouched.

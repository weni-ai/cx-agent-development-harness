# Scenario: order-status-medium

Exercises credentials/constants collection, the Retail Setup proxy, broadcasts, and
FinalResponse. Needs a Weni project with Retail Setup connected to a VTEX store.

## Prompt

/weni:new-agent Build an "order-status" collaborator for WhatsApp. Given a VTEX order ID it
fetches the order through the Retail Setup proxy and replies with the status, items,
and estimated delivery date, then sends a quick-reply broadcast with "Track another
order" and "Talk to a human". It must never reveal another customer's order.

## Watch for

- Intake asks Retail Setup proxy vs. direct VTEX credentials.
- Tool uses `Bearer` auth for Retail Setup and returns FinalResponse after the broadcast.
- Guardrail about other customers' orders appears in the eval.

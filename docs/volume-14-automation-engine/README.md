# Volume 14 — Automation Engine

Status: ⬜ Not started (skeleton).

Rules/trigger/action framework underlying the sidebar's "Automations" nav item and Marketing's automation flows (Vol 2.5) — merchant-configurable "when X happens, do Y" logic without code.

## Planned modules/pages
- Trigger library (order events, inventory events, customer events, schedule-based, webhook-based)
- Condition builder (visual rule editor)
- Action library (send email/SMS, apply tag, adjust inventory, create task, call webhook, trigger AI action)
- Automation templates (abandoned cart, win-back, low-stock reorder alert, welcome series)
- Execution log & debugging (per-run trace for troubleshooting why an automation did/didn't fire)
- Rate limiting & safety guards (prevent runaway automations, e.g., infinite trigger loops)

## Dependencies
Consumed by Marketing (Vol 2.5), Orders (Vol 2.2) for fulfillment automations, Inventory (Vol 9) for reorder automations; AI Platform (Vol 13) for AI-driven actions.

## Next steps
Define the trigger/condition/action data model and the loop-prevention safety mechanism first — both are prerequisites for any specific automation template.

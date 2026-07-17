# Volume 13 — AI Platform

Status: ⬜ Not started (skeleton).

The shared AI infrastructure powering every "AI opportunities" section across this documentation set — the Dashboard's AI Business Assistant (Vol 2.1) is the first surfaced entry point, but the platform itself is centralized here so every volume calls a common set of AI primitives rather than reinventing them.

## Planned modules/pages
- Conversational assistant framework (the engine behind "Ask AI Assistant" — context injection, tool-calling into domain APIs, streaming responses)
- Forecasting service (demand, cash flow, churn — consumed by Vol 2.1, 9, 12)
- Recommendation engine (product recommendations, next-best-action, pricing suggestions)
- Content generation (product copy, marketing copy, SEO — consumed by Vol 2.3, 2.5, 2.12)
- Anomaly detection framework (consumed by nearly every volume's "AI opportunities" section)
- Model governance (prompt/version management, evaluation, cost tracking, PII redaction policy referenced in Vol 2.1's Security section)
- Agentic automation (AI that takes actions, not just answers — ties tightly to Automation Engine Vol 14)

## Dependencies
Analytics (Vol 2.7) rollups as a primary data source, Automation Engine (Vol 14) for action execution, every domain volume as both a data source and a consumer.

## Next steps
Document the conversational assistant framework's context/tool-calling architecture first, since the Dashboard AI Assistant (Vol 2.1) is already built against it in the reference UI and needs a concrete backend contract.

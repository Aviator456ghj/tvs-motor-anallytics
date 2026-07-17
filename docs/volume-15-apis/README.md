# Volume 15 — APIs

Status: ⬜ Not started (skeleton).

The public developer-facing API surface (REST/GraphQL/webhooks) — distinct from each volume's internal "APIs" section (which documents the endpoints backing that specific Admin page). This volume is the unified, versioned, publicly-documented contract that third-party apps (Vol 2.9) and headless storefronts (Vol 3) build against.

## Planned modules/pages
- REST API reference (versioning strategy, pagination, rate limiting, error format)
- GraphQL API (schema, query complexity limits)
- Webhooks (topic catalog, delivery/retry guarantees, signature verification)
- Authentication (OAuth scopes catalog — the source of truth for Vol 2.9's scope list)
- SDKs (per-language client libraries)
- API changelog & deprecation policy

## Dependencies
Every volume's domain APIs are aggregated/exposed here; Apps (Vol 2.9) is the primary consumer-management UI; Settings (Vol 2.10) is where API keys are issued.

## Next steps
Establish the versioning/deprecation policy and error-response contract first — these are cross-cutting decisions every other volume's endpoint list must conform to.

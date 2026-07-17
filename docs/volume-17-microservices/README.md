# Volume 17 — Microservices

Status: ⬜ Not started (skeleton).

Service-boundary architecture: how the domain volumes (Orders, Inventory, Finance, AI Platform, etc.) map to deployable services, and how they communicate.

## Planned modules/pages
- Service boundary map (which volume/module = which service — e.g., OMS Vol 7, Inventory Vol 9, Finance Vol 12 as separate services)
- Inter-service communication (sync REST/gRPC vs. async event bus — the `Events` section in every Volume 2 page implies an event bus this volume must formally define)
- Event schema registry (canonical definitions for `order.created`, `product.updated`, etc. referenced throughout Volume 2)
- Service-level API gateway & BFF (backend-for-frontend) layer for Merchant Admin
- Resilience patterns (circuit breakers, retries, bulkheads — referenced in each volume's "Error handling" sections)
- Data ownership & consistency boundaries (which service owns which table from Volume 16's ERD)

## Dependencies
Database (Vol 16) for data ownership boundaries, APIs (Vol 15) for the external contract, DevOps (Vol 19) for deployment topology.

## Next steps
Formalize the event schema registry first — nearly every Volume 2 page already references specific event names in its "Events" section; this volume should make those contracts authoritative.

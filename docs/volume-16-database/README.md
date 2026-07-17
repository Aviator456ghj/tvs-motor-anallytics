# Volume 16 — Database

Status: ⬜ Not started (skeleton).

Consolidated data architecture: the full ERD spanning every volume's "Database schema" section, plus cross-cutting concerns (multi-tenancy, partitioning, migrations) that don't belong to any single domain volume.

## Planned modules/pages
- Full entity-relationship diagram (aggregating all ~300+ tables across volumes)
- Multi-tenancy strategy (shared schema with `store_id` row-level scoping — the pattern already used throughout Volume 2's schemas — vs. schema-per-tenant tradeoffs)
- Partitioning & archival strategy (e.g., `ledger_transactions`, `audit_log` growth)
- Migration/versioning process
- Read-replica & reporting-store strategy (feeds Analytics Vol 2.7 rollup tables)
- Data retention & deletion policy (GDPR/CCPA — ties to Customers Vol 2.4 anonymization)

## Dependencies
Every volume contributes schema; this volume is the integration/consistency layer (naming conventions, foreign key conventions, shared audit_log pattern already established in Vol 2's "Cross-cutting audit logging" section).

## Next steps
Produce the consolidated ERD from the schemas already defined across Volume 2's 13 pages as the first concrete artifact, then extend as later volumes are authored.

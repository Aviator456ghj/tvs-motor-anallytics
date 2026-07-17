# 2.4 Customers

## Purpose
Unified customer record — profile, order history, marketing consent, and behavioral signals — functioning as a lightweight CRM inside Merchant Admin (deep CRM capability lives in Volume 10).

## Navigation
Sidebar `Customers`. Sub-tabs: All Customers, Segments, Company Accounts (B2B, links to Vol 2.13). Customer detail route `/customers/{id}` with tabs: Overview, Orders, Segments/Tags, Notes, Marketing consent.

## User roles
Owner/Manager: full CRUD + export. Support: view + edit contact info + notes, no delete/export. Marketing: view + segment management + consent fields. Finance: view order/payment history only.

## Permissions
`customers.view`, `customers.edit`, `customers.delete` (soft-delete/anonymize, GDPR-driven), `customers.export`, `customers.merge` (dedupe).

## Fields
Name, email, phone, default address, additional addresses, tags, marketing consent (email/SMS, opt-in source, timestamp), total orders, total spent, average order value, last order date, customer since, notes (internal), risk flag, tax-exempt status, assigned segments.

## Buttons
Add customer, Edit, Merge duplicates, Add note, Add tag, Send email, Export, Delete/anonymize, Add to segment.

## Tables
List: name, email, location, orders count, total spent, tags, last order date. Order history sub-table within detail view.

## Filters
Tag, segment, location (country/region), total spent range, order count range, marketing consent status, customer since date range, has-account vs. guest.

## Search
Name, email, phone, order number (jumps to that customer).

## Bulk actions
Bulk tag, bulk add to segment, bulk export, bulk email (via Marketing), bulk consent update (compliance-driven only, audited heavily).

## Workflows
1. Customer places first order (any channel) → record auto-created → appears in Customers with `customer_since` = first order date.
2. Staff manually creates customer (e.g., phone order) → optional invite to create storefront account.
3. Merge flow: staff selects 2+ suspected-duplicate records → system shows conflict diff → staff resolves field-by-field → orders/history reassigned to surviving record, merge logged.
4. GDPR erasure request → customer anonymized (PII scrubbed, order records retained for accounting with anonymized reference).

## Business rules
- Merging customers reassigns all orders/notes/segment membership to the surviving ID; the merged-away ID is retained as an alias for lookup continuity.
- Marketing consent cannot be bulk-opted-in by staff — opt-in must originate from the customer (checkbox, double opt-in for email where required by law); staff can only opt customers *out* in bulk.
- Deleting a customer with order history performs anonymization, not hard delete, to preserve financial/audit records.

## Validation
Valid email format required if email provided; at least one contact method (email or phone) required to create a record; duplicate email triggers a "possible duplicate" warning (not a hard block, since guest checkouts can share emails legitimately in edge cases like shared family accounts).

## Notifications
New customer created, high-value customer's first order, consent change confirmation to customer, merge completed summary to staff.

## Audit logs
`customer.created/updated/deleted/merged`, `customer.consent_changed` (critical for compliance — always logged with source/IP/timestamp), `customer.note_added`, `customer.exported`.

## Database schema
```
customers(id, store_id, first_name, last_name, email, phone, accepts_marketing,
          marketing_consent_source, tax_exempt, total_spent, orders_count,
          created_at, updated_at, anonymized_at)
customer_addresses(id, customer_id, is_default, ...address fields)
customer_tags(customer_id, tag)
customer_segments(id, store_id, name, rule_definition jsonb)  -- dynamic segment rules
customer_segment_members(segment_id, customer_id)             -- static/snapshot segments
customer_notes(id, customer_id, author_id, body, created_at)
customer_merges(id, surviving_customer_id, merged_customer_id, actor_id, created_at)
```

## APIs
`GET/POST /api/v1/customers`, `GET/PATCH/DELETE /api/v1/customers/{id}`, `POST /api/v1/customers/merge`, `GET /api/v1/customers/export`, `POST /api/v1/customers/{id}/consent`. Webhooks: `customers/create`, `customers/update`, `customers/delete`.

## Events
`customer.created`, `customer.updated`, `customer.merged`, `customer.consent_changed`, `customer.segment_membership_changed` — consumed by Marketing (Vol 2.5), CRM (Vol 10), Analytics.

## Edge cases
Guest checkout with no account (record still created for order history, flagged `guest: true`); email reused across genuinely different people (shared inbox) — merge tooling must not force-merge automatically; customer requests data export (GDPR/CCPA) — separate from CSV export, must include ALL held data across volumes, not just this table.

## Error handling
Merge conflict where both records have conflicting non-null values on a required field → staff must resolve before merge completes (no silent overwrite). Export job failure → retryable, staff notified with partial-file safeguard (don't deliver truncated exports).

## Performance
Customer list paginated/indexed on email, phone, total_spent; segment rule evaluation runs as background job for dynamic segments >10k members, not synchronously on page load.

## Security
PII field-level access logging; export requires `customers.export` + is itself logged with requester and row count; anonymization is irreversible and requires Owner confirmation.

## AI opportunities
Predicted CLV and churn risk scoring (feeds Dashboard Vol 2.1); AI-suggested segments ("customers likely to buy X next"); auto-drafted personalized outreach; smart duplicate detection beyond exact-match email/phone (fuzzy name+address matching).

## UX improvements
Timeline view merging orders + notes + marketing touches in one feed; inline segment membership preview while building rules; one-click "view as this customer" for storefront QA.

## Estimated scope
~6 sub-views, ~9 API endpoints, 6 DB tables, ~30 functional requirements.

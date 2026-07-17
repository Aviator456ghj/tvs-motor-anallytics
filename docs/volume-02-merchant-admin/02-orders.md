# 2.2 Orders

## Purpose
Central hub for the full order lifecycle — from placement through payment capture, fulfillment, shipping, returns, and refunds. This is where staff spend the most operational time day-to-day.

## Navigation
- Sidebar item `Orders` with live unread/unfulfilled count badge (e.g., "54").
- Sub-tabs: All, Unfulfilled, Unpaid, Open, Closed, Returns/Refunds, Drafts, Abandoned Checkouts.
- Order detail is a dedicated route (`/orders/{id}`), not a modal, so it's linkable/shareable internally.

## User roles
Owner/Manager: full read/write incl. cancel/refund. Support: read/write on fulfillment + customer communication, refund requires Manager approval above a configurable threshold. Finance: read all, write on payment/refund records only. Marketing: read-only. App/API: scoped via OAuth (`read_orders`, `write_orders`).

## Permissions
`orders.view`, `orders.create` (manual/draft orders), `orders.edit`, `orders.fulfill`, `orders.cancel`, `orders.refund` (often gated by an approval limit, e.g., staff can refund ≤$100 unassisted), `orders.export`, `orders.delete` (drafts only; placed orders are voided/canceled, never hard-deleted).

## Fields
Order #, customer, channel, items (SKU, qty, price, tax, discount applied), subtotal/shipping/tax/discount/total, payment status (Pending/Authorized/Paid/Partially Refunded/Refunded/Voided), fulfillment status (Unfulfilled/Partial/Fulfilled/Cancelled), shipping address, billing address, shipping method, tracking number(s), tags, notes (internal), customer note, risk flag, placed_at, updated_at.

## Buttons
Create order (manual/draft), Fulfill, Mark as paid, Capture payment, Refund, Cancel order, Print packing slip/invoice, Send invoice, Duplicate order, Add tag, Add note, Export (CSV), Edit shipping address, Resend confirmation email.

## Tables
Orders list: Order #, Date, Customer, Channel, Payment status (badge), Fulfillment status (badge), Total, Items count, Tags. Sortable columns, saved views. Order detail: Line items table with per-line fulfillment/refund state.

## Filters
Date range, payment status, fulfillment status, channel, tag, fulfillment location, delivery method, risk level, customer, sales rep, has-note, saved/custom filter combinations (persisted per user).

## Search
Order number, customer name/email/phone, product name/SKU within line items, tracking number.

## Bulk actions
Bulk fulfill, bulk print packing slips, bulk tag, bulk export, bulk cancel (drafts/unpaid only), bulk archive.

## Workflows
1. Order placed (any channel) → `order.created` event → appears in Unfulfilled with payment status.
2. Payment captured (auto or manual) → status → Paid → eligible for fulfillment.
3. Staff fulfills (full or partial, single or split shipment) → tracking added → `order.fulfilled` → customer notified.
4. Return initiated (RMA, see OMS Vol.7 for deep flow) → refund issued → ledger entry created (Finance).
5. High-risk order flagged by fraud check → held pending manual review before fulfillment is allowed.

## Business rules
- Cannot fulfill an order with $0 captured payment unless "Payment on delivery" or manually overridden by Manager+.
- Partial refunds cannot exceed the remaining refundable amount (captured − already refunded).
- Cancelling a fulfilled order requires initiating a return first; cannot cancel-and-forget once shipped.
- Inventory is decremented at fulfillment time by default (configurable to decrement at order-paid time in Settings).
- Tax recalculates if shipping address is edited before fulfillment; locked after fulfillment.

## Validation
- Refund amount ≤ captured − previously refunded.
- Cannot edit line items after fulfillment (must return + reorder).
- Shipping address requires valid country/region combination and postal code format per country.
- Manual order requires ≥1 line item and a customer or guest contact.

## Notifications
Customer: order confirmation, payment receipt, shipment/tracking, delivery, refund confirmation. Staff: new high-value order, failed payment, fraud-flagged order, SLA breach (unfulfilled > X hours).

## Audit logs
`order.created/edited/cancelled/refunded/fulfilled/note_added/tag_added` — actor, before/after, timestamp; refunds additionally log approver if above staff limit.

## Database schema
```
orders(id, store_id, order_number, customer_id, channel, status, payment_status,
       fulfillment_status, subtotal, shipping_total, tax_total, discount_total,
       total, currency, risk_level, placed_at, cancelled_at, created_at, updated_at)
order_line_items(id, order_id, product_id, variant_id, sku, name, qty, unit_price,
                  tax_amount, discount_amount, fulfilled_qty, refunded_qty)
order_addresses(id, order_id, type[shipping|billing], ...address fields)
order_payments(id, order_id, gateway, status, amount, captured_at, gateway_txn_id)
order_refunds(id, order_id, amount, reason, initiated_by, created_at)
order_fulfillments(id, order_id, location_id, tracking_number, carrier, status, shipped_at)
order_tags(order_id, tag)
order_notes(id, order_id, author_id, body, internal boolean, created_at)
```

## APIs
`GET/POST /api/v1/orders`, `GET/PATCH /api/v1/orders/{id}`, `POST /api/v1/orders/{id}/fulfill`, `POST /api/v1/orders/{id}/refund`, `POST /api/v1/orders/{id}/cancel`, `POST /api/v1/orders/{id}/capture`, `GET /api/v1/orders/{id}/timeline`, webhooks: `orders/create`, `orders/updated`, `orders/fulfilled`, `orders/cancelled`, `orders/refunded`.

## Events
`order.created`, `order.paid`, `order.fulfilled`, `order.partially_fulfilled`, `order.cancelled`, `order.refunded`, `order.risk_flagged`, `order.note_added` — consumed by Dashboard, Inventory, Finance, CRM.

## Edge cases
Split shipments across multiple locations; partial payment gateways (buy-now-pay-later) with delayed capture; currency mismatch on refund (FX rate drift); customer deleted after order placed (retain order with anonymized reference); duplicate webhook delivery (idempotency key required); order placed during price/tax rule change (snapshot pricing at order time, never recompute retroactively).

## Error handling
Payment gateway timeout during capture → order held "Payment processing," retried with backoff, staff alerted if unresolved after N minutes. Fulfillment API (carrier) failure → order stays "Ready to ship" with a visible error banner and manual tracking entry fallback.

## Performance
Orders list paginated (cursor-based) with server-side filtering; target p95 < 400ms for first page of 50. Order detail loads line items + timeline in parallel, not serially.

## Security
Row-level scoping by `store_id`; PII (address, phone) field-level access logged; refund actions require re-auth (step-up) above a configurable amount; exported CSVs watermarked/logged with requester.

## AI opportunities
Auto-draft customer service replies for order inquiries; fraud-risk scoring with explainable factors; predicted fulfillment delay alerts; auto-suggested split-shipment optimization to minimize cost.

## UX improvements
Inline timeline view combining order/payment/fulfillment/communication history; keyboard shortcuts for fulfill/print in list view; saved filter presets shareable across staff.

## Estimated scope
~9 sub-views, ~14 API endpoints, 7 DB tables, ~40 functional requirements.

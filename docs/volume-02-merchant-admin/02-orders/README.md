# 2.2 Orders

Central hub for the full order lifecycle — from placement through payment capture, fulfillment, shipping, returns, and refunds. This is where staff spend the most operational time day-to-day, so unlike Dashboard (Volume 2.1, a single screen) Orders is documented and built as a **9-screen module**. Each screen gets its own full-depth spec as it's built; this page is the module-level index and the cross-cutting rules that apply to every screen in it.

## Screens

| # | Screen | Status | Notes |
|---|---|---|---|
| 2.2.1 | [Orders Dashboard](./01-orders-dashboard.md) | ✅ Built | List + inline detail panel — reference implementation at `/web/src/app/orders/page.tsx` |
| 2.2.2 | Create Order | ⬜ Not started | Manual/POS/phone order entry |
| 2.2.3 | Order Details (full page) | ⬜ Not started | Dedicated `/orders/{id}` route — the Dashboard's inline panel is the v1 preview of this |
| 2.2.4 | Fulfillment Center | ⬜ Not started | Pick/pack/ship queue across locations |
| 2.2.5 | Returns (RMA) | ⬜ Not started | Return initiation, inspection, disposition |
| 2.2.6 | Refund Center | ⬜ Not started | Refund queue, approval workflow, ledger tie-in |
| 2.2.7 | Draft Orders | ⬜ Not started | Unplaced/quote-stage orders |
| 2.2.8 | Bulk Operations | ⬜ Not started | Job status/history for bulk actions triggered from 2.2.1 |
| 2.2.9 | Order Settings | ⬜ Not started | Order number format, default statuses, SLA thresholds |

## Cross-cutting rules (apply across all 9 screens)

### User roles
Owner/Manager: full read/write incl. cancel/refund. Support: read/write on fulfillment + customer communication, refund requires Manager approval above a configurable threshold. Finance: read all, write on payment/refund records only. Marketing: read-only. App/API: scoped via OAuth (`read_orders`, `write_orders`).

### Permissions
`orders.view`, `orders.create` (manual/draft orders), `orders.edit`, `orders.fulfill`, `orders.cancel`, `orders.refund` (gated by an approval limit, e.g. staff can refund ≤$100 unassisted), `orders.export`, `orders.delete` (drafts only; placed orders are voided/cancelled, never hard-deleted), `orders.manage_settings` (Screen 2.2.9, Owner/Manager only).

### Business rules
- Cannot fulfill an order with $0 captured payment unless "Payment on delivery" or manually overridden by Manager+.
- Partial refunds cannot exceed the remaining refundable amount (captured − already refunded).
- Cancelling a fulfilled order requires initiating a return first; cannot cancel-and-forget once shipped.
- Inventory is decremented at fulfillment time by default (configurable to decrement at order-paid time in Order Settings, Screen 2.2.9).
- Tax recalculates if shipping address is edited before fulfillment; locked after fulfillment.
- Payment status and Fulfillment status are always tracked and displayed independently (an order can be Paid + Unfulfilled, or Refunded + Fulfilled) — never collapsed into one combined "status."

### Notifications
Customer: order confirmation, payment receipt, shipment/tracking, delivery, refund confirmation. Staff: new high-value order, failed payment, fraud-flagged order, SLA breach (unfulfilled > X hours).

### Audit logs
`order.created/edited/cancelled/refunded/fulfilled/note_added/tag_added` — actor, before/after, timestamp; refunds additionally log the approver if above the staff limit. Every bulk action (Screen 2.2.1 §6 / 2.2.8) logs `order.bulk_action` with the action key, affected order IDs, and actor.

### Database schema (module-wide)
```
orders(id, store_id, order_number, customer_id, channel, status, payment_status,
       fulfillment_status, subtotal, shipping_total, tax_total, discount_total,
       total, currency, risk_level, placed_at, cancelled_at, created_at, updated_at)
order_line_items(id, order_id, product_id, variant_id, sku, name, qty, unit_price,
                  tax_amount, discount_amount, fulfilled_qty, refunded_qty)
order_addresses(id, order_id, type[shipping|billing], ...address fields)
order_payments(id, order_id, gateway, status, amount, captured_at, gateway_txn_id)
order_refunds(id, order_id, amount, reason, initiated_by, created_at)
order_shipments(id, order_id, location_id, tracking_number, carrier, status, shipped_at)
order_tracking(id, shipment_id, event, location, occurred_at)
order_timeline(id, order_id, step, occurred_at)
order_notes(id, order_id, author_id, body, type[internal|customer|ai], created_at)
order_tags(order_id, tag)
order_discounts(id, order_id, discount_id, amount_applied)
order_audit_logs(id, order_id, actor_id, action, before jsonb, after jsonb, created_at)
```
Screen-specific tables (e.g., bulk-job tracking for 2.2.8) are documented on their own screen page as they're built.

### APIs (module-wide)
`GET/POST /api/v1/orders`, `GET/PATCH /api/v1/orders/{id}`, `POST /api/v1/orders/{id}/fulfill`, `POST /api/v1/orders/{id}/refund`, `POST /api/v1/orders/{id}/cancel`, `POST /api/v1/orders/{id}/capture-payment`, `POST /api/v1/orders/{id}/timeline`, `DELETE /api/v1/orders/{id}`, `GET /api/v1/orders/export`, webhooks: `orders/create`, `orders/updated`, `orders/fulfilled`, `orders/cancelled`, `orders/refunded`.

### Events
`order.created`, `order.paid`, `order.fulfilled`, `order.partially_fulfilled`, `order.cancelled`, `order.refunded`, `order.risk_flagged`, `order.note_added` — consumed by Dashboard (Vol 2.1), Inventory (Vol 9), Finance (Vol 2.8/12), CRM (Vol 10).

### Security
Row-level scoping by `store_id`; PII (address, phone) field-level access logged; refund actions require re-auth (step-up) above a configurable amount; exported CSVs watermarked/logged with requester.

# 2.2.3 Order Details

Reference implementation: `/web/src/app/orders/[id]/page.tsx` + `/web/src/components/orders/detail/*` + `/web/src/lib/order-detail-data.ts`.

Status: ✅ Built. The central operational hub of the Orders module — every team (Sales, Support, Warehouse, Finance, Customer Service) works from this page. The Orders Dashboard's inline panel (2.2.1) is the quick-glance preview; this is the full 360° record.

## Purpose
Provide a 360° operational view of a single order, allowing authorized users to monitor, update, fulfill, invoice, refund, communicate, and audit the complete order lifecycle without leaving the page.

## Navigation
- Route `/orders/{id}` (dynamic segment). Breadcrumb: `Dashboard > Orders > Order #ORD-XXXX`.
- Entry points: clicking an order number anywhere it appears — the Orders Dashboard table (2.2.1), Recent Orders on the Dashboard (Vol 2.1), Customer order history (Vol 2.4) — plus Previous/Next order navigation in this page's own header.
- All 11 tabs load in place without a page navigation.

## User roles & Permissions
| Action | Owner | Admin | Sales | Warehouse | Finance | Support | Read Only |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| View Order | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Edit Order | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Capture Payment | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Fulfill Order | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Refund Order | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Cancel Order | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| View Audit Logs | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |

Note the deliberate separations: Warehouse can fulfill but not edit or see money actions; Finance can capture/refund but not edit or fulfill; Support can cancel (customer-request path) and read audit logs but touch nothing else. The Logs tab is hidden entirely (not disabled) for roles without `orders.view_audit_logs`.

## Layout

**1. Header** — Order number + **three independent status badge groups** (see §2), breadcrumb, meta strip (order date | sales channel | customer | customer-since), and actions: Print, Email, More Actions dropdown, Previous/Next order arrows.

**2. Status badges** — three independent state machines, never collapsed into one:
- *Payment*: Pending / Authorized / Paid / Partially Paid / Refunded / Voided / Failed
- *Fulfillment*: Unfulfilled / Processing / Picking / Packing / Ready to Ship / Partially Fulfilled / Shipped / Delivered / Completed
- *Order*: Draft / Confirmed / On Hold / Cancelled / Archived

**3. More Actions dropdown** — Edit Order, Duplicate, Capture Payment, Refund, Cancel, Archive, Delete, Generate Invoice, Generate Packing Slip, Generate Shipping Label, Download PDF, Audit Logs. Destructive actions (Cancel, Delete) render in red. Each item is permission-gated per the matrix above.

**4. KPI summary strip (5)** — Order Total (+item count), Paid Amount (+date), Fulfilled (X of Y items + status), Expected Delivery (+carrier), Tracking Number (+live tracking status).

**5. Navigation tabs (11)** — Overview, Items, Payments, Shipments, Invoices, Returns, Notes, Timeline, Activity, Logs — with live counts on countable tabs.

**6. Overview tab** — three-column layout + full-width items table:
- *Customer Information*: avatar, name, VIP badge, email, phone, Total Orders, Total Spent, Outstanding (red when > 0), View full customer profile link.
- *Billing Address* and *Shipping Address* cards (shipping adds Method, Tracking + copy button + In Transit badge, Warehouse, Package Weight, carrier deep link).
- *Order Status* stepper: Order Placed → Payment Captured → Order Confirmed → Processing → Shipped → Out for Delivery → Delivered → Completed, timestamps on completed steps.
- *Order Summary*: Items Total, Discount (with coupon code), Shipping, Tax, Grand Total, Paid, Due — recalculates automatically if the order is edited.
- *Payment Information*: method, transaction ID, captured-on, status badge.
- *Tags*: color-coded chips + Add Tag.
- *Items table*: image, name/variant, SKU, price, qty, fulfilled state (✓ or Pending), line total, per-row `⋮` menu (Edit Quantity, Replace Product, Split Item, Remove Item), Add Item / Edit Items.

**7. Items tab** — the same table in extended mode, adding Reserved and Returned columns.

**8. Payments tab** — transaction table (type, method, gateway, transaction ID, amount, status, date) + Capture / Void / Refund / Retry Payment actions.

**9. Shipments tab** — per-shipment card: carrier/service/tracking/status/item-count/dates + a tracking-event sub-timeline (label created → picked up → in transit) + carrier deep link.

**10. Invoices tab** — generated documents list (ID, type, amount, status, date, download) + Generate Invoice.

**11. Returns tab** — returns list; empty state explains "Returns become available once the order is delivered" (per Business rules).

**12. Notes tab** — two sections side by side: **Customer Notes** (visible to customer) and **Internal Notes** (staff-only), each labeled with its visibility and independently addable.

**13. Timeline tab** — chronological operational events (Order Created → Payment Authorized → Payment Captured → Order Confirmed → Inventory Reserved → Picking Started → Packed → Shipping Label Created → Shipped …), each with **timestamp, user, department chip, and note** per the spec.

**14. Activity tab** — human-readable change feed (notes added, tags changed, emails sent) with actor + time — the curated counterpart to the Logs tab.

**15. Logs tab** — compliance-grade audit table: action (machine-readable key), actor, before, after, IP, time. This is the order-scoped view of the module-wide `order_audit_logs` (Vol 2.2 README).

**16. Right sidebar** — Quick Actions (Edit Order, Duplicate Order, Print Invoice, Print Packing Slip, Send Email, Add Note, Cancel Order in red), Order Notes preview (both note types, Add Note, View all), dismissible AI Insights card (high-value customer, partial fulfillment, upsell suggestion).

## Workflows
1. **Support call**: agent opens the order from a customer email search → Overview answers 90% of questions (status stepper, tracking, payment) → adds an Internal Note about the call → Activity records it.
2. **Warehouse exception**: packer finds one item damaged → opens Items tab → Split Item to ship the good unit now → fulfillment flips to Partially Fulfilled → Timeline logs the pack event with their name and department.
3. **Finance refund**: Finance opens Payments tab → Refund → amount validated against captured − already-refunded (module-wide rule) → payment status → Partially Refunded/Refunded → ledger entry created (Vol 2.8/12).
4. **Invoice request**: customer asks for an invoice → staff opens Invoices tab → Generate Invoice → Download/Email it — no leaving the page.
5. **Dispute investigation**: Support opens Logs tab → full before/after audit trail with actors and IPs answers "who changed what, when."

## Business rules
- Only confirmed orders can be fulfilled.
- Fully refunded orders cannot be edited (view-only except notes/tags).
- Cancelled orders release reserved inventory automatically.
- Delivered orders become eligible for returns — the Returns tab's empty state states this explicitly.
- Archived orders are read-only.
- Every modification creates an audit log entry (visible in the Logs tab).
- The three status dimensions (payment/fulfillment/order) transition independently — e.g., Refunded + Delivered + Archived is a legal combination.

## Validation
Refund ≤ captured − already refunded (module-wide). Item quantity edits blocked after that line is fulfilled (return instead). Tag names deduplicated case-insensitively. Note bodies non-empty.

## Notifications
Triggers: Payment Captured, Order Updated, Shipment Created, Delivery Completed, Refund Issued, Order Cancelled, Customer Note Added. Channels: Email, SMS, Push Notification, WhatsApp, Webhook — per-customer channel preference (Vol 2.4) and per-store channel enablement (Vol 2.10) decide which fire.

## Audit logs
Everything (see Business rules). Additionally `order.viewed` is logged for high-sensitivity contexts (configurable — some stores want read-access trails on high-value orders), and `order.pdf_downloaded` / `order.invoice_generated` capture document egress.

## Database schema
Reads/writes the module-wide tables (Vol 2.2 README): `orders`, `order_items`, `order_addresses`, `order_payments`, `order_refunds`, `order_shipments`, `order_tracking`, `order_timeline`, `order_notes`, `order_tags`, `order_audit_logs`. Adds:
```
payment_transactions(id, order_payment_id, type[authorize|capture|void|refund|retry],
                      gateway, gateway_txn_id, amount, status, created_at)
order_invoices(id, order_id, invoice_number, type, amount, status, pdf_url, created_at)
customer_order_history(customer_id, order_id, denormalized_summary jsonb)  -- fast prev/next + profile views
```

## APIs
`GET /api/v1/orders/{id}`, `PUT /api/v1/orders/{id}`, `POST /api/v1/orders/{id}/capture-payment`, `POST /api/v1/orders/{id}/cancel`, `POST /api/v1/orders/{id}/archive`, `POST /api/v1/orders/{id}/invoice`, `POST /api/v1/orders/{id}/packing-slip`, `POST /api/v1/orders/{id}/shipping-label`, `GET /api/v1/orders/{id}/timeline`, `GET /api/v1/orders/{id}/audit-logs`.

## Events
Emits `order.updated`, `payment.captured/voided/refunded`, `shipment.created`, `invoice.generated`, `order.cancelled/archived` — consumed by Orders Dashboard (2.2.1 live refresh), Dashboard (Vol 2.1), Inventory (release on cancel), Finance (ledger), CRM (customer timeline).

## Edge cases
- Order with zero shipments/invoices/returns: those tabs show purposeful empty states (with the returns-eligibility rule explained), never blank panels.
- Multi-shipment order (split across warehouses): Shipments tab renders one card per shipment, each with its own tracking sub-timeline.
- Guest-checkout order: Customer Information card shows contact details with a "Guest" marker instead of profile stats; "View full customer profile" is absent.
- Legal-but-unusual status combinations (Refunded + Delivered): all three badges render independently; nothing tries to reconcile them into one.
- **Known v1 gap**: the dynamic route accepts any `{id}` but the reference build always renders the ORD-2843 mock — a real backend keys the fetch on the param. Prev/Next arrows are present but static for the same reason.
- **Known v1 gap**: action buttons (Capture/Void/Refund, item row actions, More Actions items) are permission-shaped UI without wired mutations yet — each maps 1:1 to an API endpoint above.

## Error handling
Order fetch failure → full-page error with retry (this page has no meaning without its record). Per-tab data failure → inline retry within the tab, others unaffected. Mutation failures (capture/refund) → inline error preserving the user's input; money actions are idempotent server-side so a retry after timeout can't double-charge/double-refund.

## Performance
Single `GET /orders/{id}` hydrates header + KPI strip + Overview; heavier tabs (Timeline, Logs) lazy-fetch on first activation and cache for the session. Prev/Next prefetches adjacent order summaries via `customer_order_history` denormalization.

## Security
Field-level gating mirrors the permission matrix (Finance-only money actions, hidden Logs tab, redacted payment internals for unauthorized roles) — enforced at the API layer, not just hidden buttons. Audit log rows are append-only. PII display (addresses, phone) is access-logged per module policy. Document generation (invoice PDF) is logged as egress.

## AI opportunities
Current: high-value-customer flag, partial-fulfillment awareness, frequently-bought-together upsell. Spec'd next: delivery delay prediction, customer sentiment (from linked support threads), refund probability scoring, suggested support responses drafted from order context.

## UX improvements
Inline edit-in-place for addresses/tags without modals; keyboard shortcuts (P print, N note, ←/→ prev-next); a sticky mini-header (order # + badges) when scrolled deep in a long tab; live-updating status stepper via events instead of refresh.

## Estimated scope (this screen)
11 tabs, 5 KPI cards, 12 More-Actions items, 7 sidebar quick actions, 4 item-row actions, 4 payment actions, ~10 API endpoints, 3 additional DB tables, 7-role × 7-action permission matrix.

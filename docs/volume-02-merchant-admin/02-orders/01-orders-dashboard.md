# 2.2.1 Orders Dashboard

Reference implementation: `/web/src/app/orders/page.tsx` + `/web/src/components/orders/*` + `/web/src/lib/orders-data.ts`.

Status: ✅ Built. This is the list-and-triage screen for the Orders module — the equivalent of Shopify's Orders index, extended with an inline detail panel, drag-free column control, and a right-hand status legend so staff rarely need to leave the screen to look up what a badge means.

## Purpose
Give staff a single screen to find any order, understand its state at a glance, and act on it — search, filter, bulk-process, or drill into full detail — without a page navigation for the common case.

## Navigation
- Route `/orders`, sidebar item `Orders` (live count badge).
- Breadcrumb: `Dashboard > Orders`.
- Clicking an order's ID or the row's eye icon loads that order into the inline **Order Detail Panel** at the bottom of the same screen rather than navigating away — full-page order detail (Screen 2.2.3) is a separate, deeper view for when inline isn't enough.

## User roles & Permissions
Inherits the module-wide model from the [Orders README](./README.md#user-roles). Screen-specific: `orders.export` gates the Export button; `orders.fulfill`/`orders.refund`/`orders.cancel` gate the corresponding row and bulk actions (visually present but disabled/hidden for roles lacking the grant, not just server-rejected).

## Layout

**1. Header** — breadcrumb, page title, Export / Import / Create Order (split button with a caret for order-type variants).

**2. KPI cards (5)** — Total Orders, Total Revenue, Average Order Value, Pending Orders, Refunds. Each card is clickable and expands an inline breakdown popover rather than navigating to Analytics:
- Total Orders → Today / This week / This month / This year
- Total Revenue → Gross sales / Net sales / Taxes / Shipping / Discounts
- Average Order Value → shows the formula (Revenue ÷ Total Orders)
- Pending Orders → Pending payment / Pending confirmation / Pending fulfillment / Pending shipment
- Refunds → Refund amount / Refund % / Refund requests / Completed refunds

**3. Order Search** — single advanced search input scoped to order number, customer, email, phone, product, SKU, tracking ID, coupon, invoice, and payment ID (implemented as one input matching across the indexed fields, not seven separate boxes).

**4. Filters** — Date, Store, Marketplace, Country, Currency, Payment Status, Fulfillment Status, Order Status, Sales Channel, Tags, Assigned Staff, Shipping Provider. v1 renders the filter group list; per-group value pickers are the next increment (tracked below under Edge Cases/known gaps).

**5. Columns** — functional show/hide control. Always-on: Order, Date, Actions. Toggleable: Customer, Channel, Items, Subtotal, Discount, Shipping, Tax, Total, Payment, Fulfillment, Risk, Tags — state held client-side (`Set<OrderColumnKey>`), persisted per-user in a future increment.

**6. Sort** — Date (Newest/Oldest), Total (High→Low/Low→High), Customer (A–Z), Risk (High→Low).

**7. Bulk actions** — enabled only when ≥1 row is selected, shows the selection count: Export, Print Invoice, Print Label, Capture Payment, Refund, Cancel, Archive, Delete, Assign Staff, Add Tag, Remove Tag, Merge Orders, Split Orders, Send Email, Send SMS, Generate Pick List. Destructive actions (Cancel, Delete) render in red.

**8. Status tabs** — All, Unfulfilled, Unpaid, Open, Closed, Cancelled, Refunded, Return requested — each with a live count; selecting one filters the table by the order's bucket membership.

**9. Order table** — checkbox, Order ID (link), Date, [toggleable columns per §5], Actions. Row actions: Eye (view → loads into detail panel), Pencil (edit), and a `⋮` menu with Duplicate, Refund, Cancel, Archive, Delete, Timeline, Audit Logs. Footer: "Showing X to Y of Z orders" + pagination.

**10. Order Detail Panel** (inline, below the table, loads the selected order): header (Order #, Payment badge, Fulfillment badge, date, channel, Print/Refund/More actions, prev/next navigation) + four columns (Customer, Order summary, Shipping address, Order timeline) + Items table + Notes.

**11. Right sidebar** — Quick Actions (Create Order, Import Orders, Export Orders, Manage Returns, Bulk Update Orders, Print Packing Slips, Print Invoices) and an Order Statuses reference panel with three color-coded legends (Payment Status, Fulfillment Status, Order Status) so staff can identify any badge on the screen without leaving it.

## Fields
Order: id, date, customer, email, phone, channel, items count, subtotal, discount, shipping, tax, total, payment status, fulfillment status, order status, risk (Low/Medium/High), tags, bucket membership (drives status-tab filtering). Detail panel adds: shipping address, order timeline steps with timestamps, line items (name, variant, SKU, price, qty, total), notes.

## Workflows
1. **Triage**: staff lands on All → scans KPI deltas → clicks the Unfulfilled tab → works down the list.
2. **Find and act**: staff searches an order number → clicks the eye icon → detail panel loads → clicks Refund.
3. **Bulk processing**: staff filters to Unpaid → selects several rows via checkbox → Bulk actions → Send Email (payment reminder).
4. **Column tuning**: staff toggles on Risk and Tags via Columns to triage fraud-flagged orders, toggles off Channel/Items to reduce clutter.
5. **Quick create**: staff clicks Create Order from the right sidebar or header button → routed to Screen 2.2.2 (not yet built).

## Business rules
Inherits all module-wide rules from the [Orders README](./README.md#business-rules). Screen-specific: the "Showing X to Y of Z" and per-tab counts reflect the *bucket's* total count (server-side), while the rendered rows are the current page's worth — a row can appear identical across pages only in the mock/reference dataset, never in the real paginated API.

## Validation
Search requires no minimum length (empty = show all); bulk action buttons are disabled (not hidden) when selection is empty, so the control is discoverable; column toggle always leaves Order/Date/Actions visible (cannot be hidden — they're the minimum viable row identity).

## Notifications
Inherits module-wide (see README). Screen-specific: a toast confirms bulk action completion with an undo window for reversible actions (Archive, Add Tag).

## Audit logs
Every row action and bulk action logs `order.<action>` per the module-wide audit spec, plus `orders_dashboard.column_visibility_changed` and `orders_dashboard.filter_applied` for UX analytics (not compliance-critical, lower retention).

## Database schema
Reads from the module-wide `orders`/`order_line_items`/etc. tables (see [Orders README](./README.md#database-schema-module-wide)). Adds:
```
user_orders_view_preferences(id, user_id, store_id, visible_columns jsonb,
                              default_sort text, default_tab text, updated_at)
```

## APIs
`GET /api/v1/orders?bucket=&search=&sort=&page=` (paginated, server-side filtered), `GET /api/v1/orders/kpis?range=`, plus the module-wide mutation endpoints (fulfill/refund/cancel/capture) invoked from row and bulk actions. `PUT /api/v1/orders-dashboard/preferences` for column/sort persistence.

## Events
Consumes `order.created/paid/fulfilled/cancelled/refunded` to keep KPI cards and tab counts live without a full page refresh (matches the Dashboard's targeted-invalidation pattern from Volume 2.1 §15).

## Edge cases
- Zero orders match the active tab+search combination → empty state with a "Clear filters" CTA, not a blank table.
- An order matches multiple buckets (e.g., Unfulfilled *and* Unpaid) → appears under both tabs; bucket membership is a set, not a single enum, by design (mirrors the fact that payment and fulfillment are independent statuses).
- User hides every optional column → table still shows Order/Date/Actions rather than collapsing to nothing.
- **Known v1 gap**: Filters button currently lists the 12 filter groups without per-group value pickers (e.g., clicking "Payment Status" doesn't yet open a checklist of statuses) — functional filtering today is via Search + Status tabs; full per-filter value UI is the next increment on this screen.
- **Known v1 gap**: pagination controls update `currentPage` state but the underlying mock dataset only has 8 orders, so pages 2+ render the same 8 rows — a real backend with true pagination resolves this; documented here so it isn't mistaken for a bug during review.

## Error handling
Failed KPI fetch → cards show a retry state individually (same per-widget error boundary pattern as Dashboard, Volume 2.1 §14). Failed bulk action → per-order success/failure breakdown in the confirmation toast rather than an all-or-nothing failure.

## Performance
Order list query is server-side paginated and filtered (never fetch-all-then-filter-client-side) — target p95 < 400ms for a page of 50. KPI cards read from the same rollup pattern as Dashboard's `analytics_daily_rollup`, not computed live from `orders` on every load.

## Security
Inherits module-wide (row-level `store_id` scoping, PII access logging, step-up auth on refunds above threshold). Column visibility and filter state are per-user, never leak between staff accounts.

## AI opportunities
Risk-score explanations inline in the Risk column; AI-drafted bulk email/SMS content for the Send Email/Send SMS bulk actions; auto-suggested bulk action based on the current filter (e.g., viewing Unpaid + selecting all → suggest "Send payment reminder"); natural-language search ("orders over $200 from Amazon this week").

## UX improvements
Saved filter+column+sort combinations as named views (e.g., "Fraud review," "Daily fulfillment queue"); keyboard shortcuts for row actions when a row is focused; drag-to-reorder columns in addition to show/hide.

## Estimated scope (this screen)
5 KPI cards, 8 status tabs, 12 toggleable columns, 16 bulk actions, 7 row actions, 4-panel inline order detail, 2 right-sidebar widgets, ~4 screen-specific API endpoints (plus the module-wide mutation endpoints), 1 additional DB table.

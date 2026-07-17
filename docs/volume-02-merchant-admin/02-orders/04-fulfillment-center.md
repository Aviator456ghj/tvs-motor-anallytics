# 2.2.4 Fulfillment Center

Reference implementation: `/web/src/app/orders/fulfillment/page.tsx` + `/web/src/components/orders/fulfillment/*` + `/web/src/lib/fulfillment-data.ts`.

Status: ✅ Built. Manages the entire warehouse fulfillment lifecycle from inventory allocation through picking, packing, shipping, and delivery. Primary users: Warehouse Team, Operations Team, Shipping Team, Logistics Manager.

## Structural change from this screen onward: the Orders Workspace Nav
Starting here, every Orders screen carries **three navigation levels**, and this is now a **permanent standard** applied retroactively to 2.1–2.3 as well as forward to 2.5–2.9:

1. **Global navigation** (left sidebar) — unchanged: Dashboard, Orders, Customers, Products, Marketing, Discounts, Content, Markets, Analytics, Finance, Apps, Automations, AI Center, Settings.
2. **Orders workspace navigation** (new) — a persistent bar directly below the top bar, present on every `/orders/*` route: Dashboard, Create Order, Order Details, Fulfillment Center, Returns (RMA), Refund Center, Draft Orders, Bulk Operations, Order Settings. The current page is highlighted in the brand color. Users never leave the Orders workspace to move between its screens.
3. **Current screen** — everything below the workspace nav belongs only to that page, as documented on each screen's own page.

**Implementation**: `app/orders/layout.tsx` (a Next.js nested layout) renders `<OrdersWorkspaceNav />` once and wraps `{children}` — so every current and future file under `app/orders/**` inherits the bar automatically without per-page duplication. `OrdersWorkspaceNav` (`components/orders/OrdersWorkspaceNav.tsx`) derives the active tab from the current pathname: exact match for `/orders`, known static segments for `create`/`fulfillment`/`returns`/`refunds`/`drafts`/`bulk`/`settings`, and anything else under `/orders/{unknown}` (i.e. an order ID) falls through to "Order Details."

## Purpose
Manage the entire warehouse fulfillment lifecycle — inventory allocation through picking, packing, shipping, and delivery — as an operational queue, not a per-order drill-down.

## Navigation
Route `/orders/fulfillment`. Breadcrumb: `Dashboard > Orders > Fulfillment Center`. Order numbers in the table link to Order Details (2.2.3).

## User roles & Permissions
| Action | Owner | Admin | Warehouse Manager | Picker | Packer | Support | Read Only |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| View Fulfillment | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create Fulfillment | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign Warehouse | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign Picker | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Mark Picked | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Mark Packed | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Generate Label | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Complete Shipment | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

Note the intentionally narrow Picker/Packer grants: a Picker can only mark items picked, a Packer can only mark items packed — neither can assign staff, generate labels, or complete shipments. This mirrors real warehouse floor roles, where cross-functional access is the exception not the default.

## Layout

**1. Header** — breadcrumb, title, Export, Print Pick List, Create Fulfillment (split button: From pending orders / Manual fulfillment / Split shipment).

**2. KPI cards (6)**, each with a breakdown popover:
- *Pending Pick* — Today's pick queue, Avg. waiting time
- *Picking* — Assigned employees, Avg. pick time
- *Packing* — Packed orders, Waiting shipment, Packing errors
- *Ready to Ship* — Ready for pickup, Courier assigned, Awaiting label
- *Shipped Today* — Completed shipments, Delayed shipments
- *Exception* — Inventory issues, Address issues, Payment hold, Carrier errors

**3. Search** — Order ID, Tracking ID, Customer, SKU, Barcode, Warehouse, Courier.

**4. Filter selects** — Warehouse, Sales Channel, Priority, Shipping Method, Status (inline dropdowns, always visible) plus a **Filters** button for the deeper set: Warehouse, Sales Channel, Priority, Shipping Method, Status, Assigned Picker, Assigned Packer, Carrier, Delivery Date (v1 lists the groups; per-group value pickers are the same known gap pattern as Screens 2.1/3.1).

**5. Status tabs (8)** — All, Pending Pick, Picking, Packing, Ready to Ship, Shipped, Exception, On Hold — each with a live count, filtering the table.

**6. Fulfillment table** — checkbox, Order (links to 2.2.3), Customer, Items (+SKU count), Warehouse (code badge + name), Status badge (+Expedited flag when applicable), Priority (↑High/•Medium/↓Low, color-coded), Shipping Method, Ship By, Picker/Packer ("Unassigned" in italics when empty), Actions (print pick list, print label, `⋮` menu: Assign Picker, Mark Picked, Put On Hold).

**7. Fulfillment Workflow strip** — Pending Pick → Picking → Packing → Ready to Ship → Shipped → Delivered, each step with an icon and one-line description, connected by arrows — a persistent visual reference for where any order sits in the pipeline.

**8. Recent Activity** and **9. Exception Orders** (side by side) — Recent Activity is a chronological feed (time, event, actor); Exception Orders lists flagged orders with reason, date, and severity (High/Medium/Low, color-coded).

**10. Right sidebar**:
- *Fulfillment Progress* — donut chart (center label: total order count) + legend with per-bucket count and percentage, matching the status tabs' buckets.
- *Warehouse Capacity* — per-warehouse usage bar (used/max units), color escalating amber→red as it approaches capacity.
- *Quick Actions* — Create Fulfillment, Print Pick List, Print Packing Slip, Create Shipping Label, Bulk Fulfill Orders.
- *AI Insights* (dismissible, "Beta" tag) — e.g. "37 orders ready to ship today," "18 exception orders require attention," "New York Warehouse capacity will reach 90% tomorrow."

## Fields
See Layout for the full per-row and per-card field list. Core fulfillment record: order ID, customer, items/SKU count, warehouse, status (bucket-driven), priority, shipping method, expedited flag, ship-by deadline, assigned picker, assigned packer.

## Workflows
1. **Morning pick run**: Warehouse Manager opens Pending Pick tab → sorts by Priority → assigns pickers via row `⋮` → Print Pick List for the batch.
2. **Pack verification**: Packer filters to Packing → marks items packed via row action → status flips to Ready to Ship, feeding the Ready to Ship KPI and donut in real time.
3. **Exception triage**: Ops sees the Exception KPI/tab spike → opens Exception Orders card → each row's reason (Payment failed, Address verification failed, Item out of stock, Carrier pickup delay, Weight mismatch) routes to the right owning team (Finance for payment holds, CRM for address issues, Inventory for stock issues).
4. **Capacity-aware routing**: Ops sees New York Warehouse at 78% (and an AI Insight flagging it'll hit 90% tomorrow) → shifts new Create Fulfillment assignments toward Dallas (40%) proactively.
5. **Label + carrier handoff**: order reaches Ready to Ship → Generate Shipping Label → Carrier Pickup recorded → Shipped, timeline/activity updated (ties into Order Details 2.2.3 Timeline tab for that specific order).

## Business rules
- Inventory must be reserved before picking (ties to the module-wide `inventory_reservations` table, Screen 2.2.2).
- Only paid or approved orders can enter fulfillment.
- Every pick operation creates an audit record.
- Partial fulfillment is allowed — an order can sit at "Partially Fulfilled" (Order Details' fulfillment status) while its remaining items are still Pending Pick here.
- Warehouse stock updates immediately after picking, not at ship time — so Inventory (Volume 9) reflects reality mid-fulfillment, not just at the bookends.
- Shipping labels can only be generated after packing.
- Delivered orders automatically complete fulfillment (closes the loop into Order Details' status stepper).
- Exception orders require manager approval before continuing — a Picker/Packer cannot clear an exception themselves.

## Automation rules
Automatic actions this screen is designed to trigger (Automation Engine, Volume 14): Assign Warehouse, Assign Picker, Assign Packer, Generate Pick List, Generate Shipping Label, Notify Customer, Update Inventory, Update Timeline.

## Validation
Mark Picked requires an assigned picker on the row. Mark Packed requires the order to be in Picking or later. Label generation blocked until Packed. Bulk Fulfill Orders validates every selected row is eligible (paid + inventory reserved) before executing, rejecting ineligible rows individually rather than failing the whole batch.

## Notifications
Triggers: Picking Started, Packing Complete, Shipment Created, Carrier Picked Up, Delivered, Fulfillment Exception. Channels: Email, SMS, Push, WhatsApp, Webhook.

## Audit logs
Every pick/pack/ship/exception transition is logged (module-wide `order_audit_logs` / here also `fulfillment_logs`), visible per-order in Order Details' Logs tab (2.2.3) and in aggregate via Recent Activity on this screen.

## Database schema
```
fulfillments(id, order_id, store_id, warehouse_id, status, priority, shipping_method,
             expedited boolean, ship_by, picker_id null, packer_id null, created_at, updated_at)
fulfillment_items(id, fulfillment_id, order_item_id, qty, picked_qty, packed_qty)
warehouse_inventory(id, warehouse_id, product_variant_id, quantity, reserved)
warehouse_locations(id, warehouse_id, name, capacity)
pick_lists(id, warehouse_id, generated_by, order_ids jsonb, created_at)
packing_lists(id, fulfillment_id, verified_by, created_at)
shipping_labels(id, fulfillment_id, carrier, service, tracking_number, cost, created_at)
shipment_tracking(id, shipping_label_id, event, location, occurred_at)
warehouse_staff(id, warehouse_id, user_id, role[picker|packer|manager])
carriers(id, name, api_config jsonb)
carrier_pickups(id, warehouse_id, carrier_id, scheduled_at, completed_at)
fulfillment_logs(id, fulfillment_id, actor_id, action, before jsonb, after jsonb, created_at)
```

## APIs
`GET /api/v1/fulfillment`, `GET /api/v1/fulfillment/{id}`, `POST /api/v1/fulfillment`, `PUT /api/v1/fulfillment/{id}`, `POST /api/v1/fulfillment/pick`, `POST /api/v1/fulfillment/pack`, `POST /api/v1/fulfillment/ship`, `POST /api/v1/shipping/label`, `GET /api/v1/pick-list`, `GET /api/v1/packing-slip`, `GET /api/v1/carrier/tracking`.

## Events
`fulfillment.created`, `fulfillment.picked/packed/shipped`, `fulfillment.exception_raised`, `inventory.level_changed` (fires on pick, not just ship) — consumed by Order Details (2.2.3 Timeline/Overview), Inventory (Volume 9), Dashboard Inventory Alerts (Volume 2.1), Customer notifications.

## Edge cases
- Order spans multiple warehouses (split shipment): each warehouse's portion appears as its own fulfillment row/record, independently progressing through the pipeline — this is why `fulfillments` is keyed separately from `orders`, not 1:1.
- Picker assigned but goes on break mid-pick: order stays "Picking" indefinitely without a stale-order alert in v1 — flagged as a gap; a real system would SLA-timeout this.
- Exception cleared but underlying cause recurs (e.g., address still invalid after a "fix"): re-flags to Exception rather than silently retrying indefinitely.
- Warehouse hits 100% capacity: Create Fulfillment should block/warn for that warehouse specifically — not yet enforced in this reference build (capacity is displayed, not gated).
- **Known v1 gap**: row actions (Assign Picker, Mark Picked, Put On Hold) and header actions (Print Pick List, Create Fulfillment) are permission-shaped UI registering clicks without wired mutations — each maps 1:1 to the API endpoints above.

## Error handling
Pick-list generation failure → retry with the same order set preserved (never silently drop orders from a requested batch). Label generation failure (carrier API down) → order stays "Ready to Ship" with a visible carrier-error banner, exception NOT auto-raised unless the failure persists past a retry threshold (transient carrier hiccups shouldn't spam the Exception queue).

## Performance
Table is server-side paginated/filtered like Orders Dashboard (2.2.1); KPI cards and the Progress donut read from a rollup rather than aggregating `fulfillments` live on every load, since this screen is expected to be left open on a warehouse floor monitor and polled/refreshed frequently.

## Security
Warehouse-scoped visibility: a Picker/Packer's view can be restricted to their assigned warehouse only (multi-warehouse operators don't want floor staff seeing other sites' queues) — modeled via `warehouse_staff.warehouse_id`. All mutations logged per Audit logs above.

## AI opportunities
The 3 shown insights (ready-to-ship reminder, exception attention, capacity forecast) are the v1 surface. Spec'd next: recommend the best warehouse based on inventory + distance to destination; suggest the fastest or lowest-cost carrier per shipment; predict shipping delays before they happen; detect bottlenecks in picking/packing queues (e.g., one picker is 3x slower than the team average today).

## UX improvements over Shopify
This is the screen where CommerceOS's differentiation becomes concrete, not aspirational:
- **Persistent workspace navigation** (this screen introduces it) — Shopify's fulfillment view requires leaving to a different admin section for related order tasks; here Dashboard → Create → Details → Fulfillment → Returns → Refunds → Drafts → Bulk → Settings stay one click apart, always.
- **AI-driven operations** — warehouse/carrier recommendation and delay prediction are native to this screen's data model (fulfillment + warehouse capacity + carrier performance all live in one place), not bolted on via a third-party app.
- **Warehouse intelligence** — live capacity monitoring and the picker/packer workload fields are structural (`warehouse_staff`, `warehouse_locations.capacity`) — future heat-map/workload-balancing views build on data this screen already collects, not a redesign.
- **SLA countdowns** (Ship By column) — visible per-row today; a future increment turns this into a live countdown/escalation rather than a static timestamp.

## Estimated scope (this screen)
6 KPI cards, 5 inline filter selects + 9-group Filters panel, 8 status tabs, 3 row actions + 2 header icon actions, 6-step workflow strip, 4 right-sidebar widgets, ~11 API endpoints, 12 DB tables, 7-role × 8-action permission matrix.

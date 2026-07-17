# 2.2.5 Returns (RMA)

Reference implementation: `/web/src/app/orders/returns/page.tsx` + `/web/src/components/orders/returns/*` + `/web/src/lib/returns-data.ts`.

Status: ✅ Built. Manages the complete Return Merchandise Authorization lifecycle: customer return requests, product replacements, return shipping, warehouse inspection, return approvals, refund processing, and return analytics. Carries the Orders Workspace Nav introduced in Screen 2.2.4, with "Returns (RMA)" active.

## Purpose
Give Support, Warehouse, and Finance a single operational queue for every return in flight — from the moment a customer requests one through inspection to its final refund, replacement, or rejection — without the disposition decision and the money movement living in separate, disconnected tools.

## Navigation
Route `/orders/returns`. Breadcrumb: `Dashboard > Orders > Returns (RMA)`. Order IDs in the table link to Order Details (2.2.3); RMA processing that results in a refund hands off to Refund Center (2.2.6, next screen).

## User roles & Permissions
| Permission | Owner | Admin | Support | Warehouse | Finance | Read Only |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| View Returns | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create RMA | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Approve Return | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Receive Return | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Inspect Product | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Approve Refund | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Generate Return Label | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

The split here is deliberate: Support decides *whether a return is legitimate* (Approve Return); Warehouse decides *what physically happened to the item* (Receive, Inspect); Finance decides *whether money moves* (Approve Refund). No single non-Owner/Admin role can request, inspect, and refund the same return — a built-in separation of duties against return fraud.

## Layout

**1. Header** — breadcrumb, title, Export, Print RMA List, Create RMA (split button: From existing order / Manual RMA / Bulk RMA import).

**2. KPI cards (5)**, each with a breakdown popover:
- *Return Requests* — Today's/Weekly/Monthly requests, Growth %
- *Approved* — Approved returns, Approval rate, Pending approval
- *In Transit* — Customer shipped, Courier pickup, Expected arrival
- *Received* — Packages received, Inspection pending, Inspection complete
- *Refund Issued* — Refund amount, Completed refunds, Replacement orders

**3. Search** — RMA ID, Order ID, Customer, SKU, Tracking Number, Email, Phone.

**4. Filter selects** — Status, Reason, Warehouse, Return Type (inline) + Requested Date range picker, plus a **Filters** button for the deeper set: Status, Reason, Warehouse, Return Type, Courier, Requested Date, Received Date, Refund Status, Customer Group (same known-gap pattern as prior screens — groups listed, value pickers pending) and a table-settings icon.

**5. Status tabs (8)** — All Returns, Requested, Approved, In Transit, Received, Refund Pending, Refunded, Rejected.

**6. Returns table** — checkbox, RMA ID (+requested timestamp), Order ID (links to 2.2.3), Customer (+email), Items (+SKU count), Reason (color-coded badge — Wrong Size, Wrong Product, Defective, Damaged, Missing Item, Changed Mind, Late Delivery, Quality Issue, Not as Described), Status (color-coded badge), Return Type (Refund/Replacement/Exchange/Store Credit/Repair), Requested On, Actions (eye + `⋮`: View Details, Approve, Reject, Generate Return Label, Mark Received, Send to Inspection).

**7. Bottom row (3 columns)**:
- *Return Details* — selected RMA's header (ID + status), Order ID/Customer/Requested On/Return Type/Reason, Notes, line items with qty, Total Refund Amount.
- *Return Activity Timeline* — Return Requested → Approved → Return Label Generated → Customer Shipped → In Transit → Warehouse Received → Inspection → Refund Approved → Refund Processed → Completed, each completed step with timestamp + actor; pending steps shown dimmed.
- *Top Returned Products* — ranked list (product, return count) — the single fastest way to spot a defect trend.

**8. Right sidebar**:
- *Returns Overview* — donut chart (center: total returns) + legend, mirroring the status buckets.
- *Reasons Summary* — horizontal bar list (Wrong Size, Defective, Not as Described, Changed Mind, Damaged, Other) with count + percentage.
- *Quick Actions* — Create RMA, Approve Return, Print Return Label, Print RMA List, Bulk Process Returns.
- *AI Insights* (dismissible, "Beta") — e.g. "32 returns are awaiting approval," "Defective returns increased by 18% this week," "High-value returns detected. Review recommended."

## Fields
See Layout for the full per-row/per-panel field list. Core return record: RMA ID, order ID, customer, items/SKU count, reason, status (bucket-driven), return type, warehouse, requested-on timestamp. Detail panel adds: notes, per-item qty/price, total refund amount.

## Workflows
1. **Customer-initiated return**: Support receives a request → Create RMA from the existing order → selects reason + return type → Approve Return → return label auto-generated → customer notified.
2. **Inspection-gated refund**: package arrives → Warehouse marks Received → performs Product Inspection (condition, packaging, accessories, serial number, damage photos, notes) → records an Inspection Result (Approved/Rejected/Needs Review) → only an Approved inspection unlocks Finance's Approve Refund.
3. **Replacement path**: RMA's Return Type is Replacement → approval automatically creates a new fulfillment task (ties into 2.2.4) rather than a refund — the customer gets a new unit shipped, no money moves.
4. **Defect trend response**: Ops notices Top Returned Products' #1 item climbing → cross-references Reasons Summary (mostly "Defective") → AI Insight flags the 18% weekly increase → routes to supplier investigation (a documented AI opportunity below, not yet automated).
5. **Fraud-aware rejection**: Support/Admin reviews a return against fraud scoring (see Business rules) → Reject with a reason → customer notified via the Return Rejected template.

## Business rules
- Only delivered orders can request returns (mirrors Order Details' Business rule, Vol 2.2.3).
- Return window is configurable (e.g., 30 days) — enforced at RMA creation, not just documented policy.
- Digital products cannot be returned.
- Warehouse inspection is required before refund approval — Finance cannot Approve Refund on a return that hasn't cleared Inspection.
- Replacement orders automatically create a new fulfillment task.
- Restock inventory only after inspection approval — a rejected or damaged-beyond-resale item never silently re-enters sellable stock.
- Fraud score is calculated before approval (serial-return customers, mismatched serial numbers, high-value pattern detection).
- Every RMA generates an audit log entry.

## Automation rules
Automatic actions this screen is designed to trigger (Automation Engine, Volume 14): Generate RMA Number, Create Return Label, Notify Warehouse, Notify Customer, Reserve Replacement Stock, Create Refund Request, Update Order Timeline, Sync Inventory.

## Validation
Return request blocked if the order isn't Delivered or the return window has expired. Reject requires a reason. Approve Refund blocked until Inspection Result = Approved. Bulk Process Returns validates each selected row's eligibility individually, same pattern as Bulk Fulfill Orders (2.2.4) — partial success, not all-or-nothing.

## Notifications
Triggers: Return Requested, Return Approved, Package Received, Inspection Completed, Refund Approved, Refund Completed, Replacement Shipped. Templates: Return Approved, Return Rejected, Return Label, Refund Processed, Replacement Shipped, Inspection Complete. Channels: Email, SMS, WhatsApp, Push Notification.

## Audit logs
Every status transition (`return.requested/approved/rejected/received/inspected/refunded`) is logged with actor, before/after, and timestamp — visible in aggregate via this screen's activity and per-RMA via the Return Activity Timeline panel.

## Database schema
```
returns(id, store_id, order_id, customer_id, rma_number, status, return_type,
        reason, warehouse_id, notes, total_refund_amount, requested_at, created_at, updated_at)
return_items(id, return_id, order_item_id, sku, qty, unit_price)
return_images(id, return_id, url, type[photo|video], uploaded_by, created_at)
return_documents(id, return_id, type, url, created_at)
return_tracking(id, return_id, carrier, tracking_number, status, updated_at)
return_labels(id, return_id, carrier, cost, label_url, created_at)
return_inspections(id, return_id, inspector_id, condition, packaging, accessories,
                    serial_number, damage_photos jsonb, notes, result[approved|rejected|needs_review], inspected_at)
return_reasons(id, store_id, label, active boolean)   -- merchant-configurable reason taxonomy
replacement_orders(id, return_id, new_order_id, created_at)
warehouse_receipts(id, return_id, warehouse_id, received_by, received_at)
return_logs(id, return_id, actor_id, action, before jsonb, after jsonb, created_at)
```

## APIs
`GET /api/v1/returns`, `GET /api/v1/returns/{id}`, `POST /api/v1/returns`, `PUT /api/v1/returns/{id}`, `POST /api/v1/returns/{id}/approve`, `POST /api/v1/returns/{id}/reject`, `POST /api/v1/returns/{id}/receive`, `POST /api/v1/returns/{id}/inspect`, `POST /api/v1/returns/{id}/complete`, `GET /api/v1/returns/export`.

## Events
`return.requested/approved/rejected/received/inspected/refunded`, `replacement.created`, `inventory.restocked` — consumed by Order Details (2.2.3 Timeline), Fulfillment Center (2.2.4, for replacement orders), Refund Center (2.2.6, next), Inventory (Volume 9), Dashboard (Volume 2.1).

## Edge cases
- Partial return (2 of 4 items from an order): `return_items` references only the returned lines; the parent order's fulfillment status stays whatever it was, only the returned SKUs' inventory/refund math is touched.
- Inspection result "Needs Review": neither auto-approved nor auto-rejected — sits in a manual-review state until a Warehouse Manager or Admin resolves it, deliberately not on a timer/auto-escalation in v1.
- Customer ships back the wrong item (serial number mismatch during inspection): inspection records the mismatch, return is flagged for manual fraud review rather than auto-rejected, since mismatches also happen from honest customer error.
- Replacement item is now out of stock: Business rule says replacement "automatically creates a new fulfillment task," but if the warehouse can't fulfill it, the return should convert to Refund instead — not yet automated in this reference build, flagged as a gap.
- **Known v1 gap**: the Return Details panel updates its header/customer/order/reason/status live when a different row is selected, but Items/Notes/Total Refund still render the sample RMA's content — full per-row detail requires a richer mock dataset than v1 ships with (same pattern as Order Details' single fully-detailed sample order).
- **Known v1 gap**: row and header actions (Approve, Reject, Generate Label, Mark Received, Send to Inspection, Create RMA) are permission-shaped UI mapped 1:1 to the API endpoints above, not wired to real mutations yet.

## Error handling
Return label generation failure (carrier API) → RMA stays "Approved," visible carrier-error state, doesn't silently block the customer from being notified that their return was approved. Inspection submission failure → inspector's notes/photos preserved client-side for retry, never lost.

## Performance
Table server-side paginated/filtered like Orders Dashboard and Fulfillment Center. KPI cards and Returns Overview donut read from a rollup, not aggregated live from `returns` on every load.

## Security
Approve Refund is the most sensitive action on this screen (money movement) and is Finance-gated independently of Approve Return (Support-gated) — a compromised Support account cannot alone trigger a refund. Damage photos/videos are access-logged like any customer-submitted media. Fraud scoring inputs (customer history, serial numbers) are logged for audit but not exposed raw to Support-level roles.

## AI opportunities (CommerceOS advantage — unlike Shopify)
- AI fraud detection for abnormal return behavior (return velocity, serial-mismatch patterns, geographic anomalies).
- Automatic return reason clustering (normalizing free-text reasons into the structured taxonomy).
- Product defect trend analysis (surfacing exactly the pattern the Top Returned Products + Reasons Summary combination hints at today, but predictively).
- Supplier quality score derived from return data, feeding back into Products (Volume 2.3) vendor records.
- Predictive return probability by product (flag high-return-risk SKUs before they ship, not after).
- AI-generated inspection summaries from a Warehouse Manager's raw notes/photos.
- Recommended refund-vs-replacement decisions based on inventory position, customer value, and item condition.

## UX improvements
Photo/video upload directly in the Return Details panel during inspection (currently modeled in schema, not yet in UI); side-by-side before/after inventory impact preview when approving a replacement; saved filter presets per role (a Warehouse view defaulting to Received+Inspection, a Finance view defaulting to Refund Pending).

## Estimated scope (this screen)
5 KPI cards, 8 status tabs, 6 row actions, 3 bottom-row panels, 4 right-sidebar widgets, 10-step return timeline, ~10 API endpoints, 11 DB tables, 6-role × 7-action permission matrix.

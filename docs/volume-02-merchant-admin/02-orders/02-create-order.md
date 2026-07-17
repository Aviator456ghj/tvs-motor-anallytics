# 2.2.2 Create Order

Reference implementation: `/web/src/app/orders/create/page.tsx` + `/web/src/components/orders/create/*` + `/web/src/lib/create-order-data.ts`.

Status: ✅ Built. A 5-step guided wizard for staff/sales/admin-created orders — phone orders, POS-adjacent manual entry, B2B orders — with full customer context, live pricing, inventory/fraud visibility, and an AI assistant entry point at every step.

## Purpose
Let staff manually create a customer order with complete control over customer selection, products, pricing, taxes, shipping, payment, discounts, inventory validation, and fraud checks — without leaving Admin or reconstructing context from memory.

## Navigation
- Route `/orders/create`. Breadcrumb: `Dashboard > Orders > Create Order`.
- Entry points wired to this screen: the Orders Dashboard header's "Create Order" button (Vol 2.2.1), its right-sidebar Quick Action, and the Dashboard's Quick Actions "Create Order" tile (Vol 2.1) — all three link here rather than opening disconnected flows.
- Screen flow: Select Customer → Add Products → Shipping Details → Payment Details → Review Order → Create Order.

## User roles & Permissions
| Action | Owner | Admin | Sales | Warehouse | Support | Read Only |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Create Order | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Save Draft | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Apply Discount | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Override Price | ✅ | ✅ | ⚠️ Configurable | ❌ | ❌ | ❌ |
| Assign Warehouse | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| View Customer History | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

Permission keys: `orders.create` (module-wide, Vol 2.2 README), `orders.save_draft`, `orders.apply_discount`, `orders.override_price` (Sales role's grant is a per-store configurable toggle, not a fixed yes/no — reflects the ⚠️ in the matrix), `orders.assign_warehouse`, `customers.view_history`.

## Layout

**1. Order Wizard** — 5-step indicator (Customer → Products → Shipping → Payment → Review), each step numbered with a connecting line that fills as steps complete. Only completed steps are clickable/re-editable; you cannot jump ahead of the furthest step reached (`maxReachedStep` gates forward navigation, not just the visual state).

**2. Header actions** — Cancel (returns to Orders Dashboard), Save Draft (creates a Draft order — see Business rules), Next Step (validates the current step before advancing; relabels to **Create Order** on step 5).

**3. Step 1 — Customer**: Existing/New Customer toggle.
- *Existing*: autocomplete search (name/email/phone) → customer card (avatar, name, Registered/Guest badge, email, phone, Total Orders, Total Spent, Outstanding balance).
- *New*: First/Last Name, Email (required), Phone, Company, GST Number, Tax ID.
- Billing Address / Shipping Address cards, each with a saved-address selector, an inline address display with Edit, an "Add New Address" action, and a **Use Shipping**/**Use Billing** checkbox that copies one address onto the other (functional — not just a visual toggle).
- Order Settings: Sales Channel, Warehouse, Order Date, Currency, Language, and an Order Priority selector (Low/Medium/High/Urgent).
- Tags: free-text + suggested chips (VIP, Wholesale, Urgent, COD, Corporate, Gift).
- Internal Notes: staff-only, 500-character max with a live counter.
- Below the fold (existing customers only): **Customer Recent Orders**, **Customer Notes** (e.g. VIP delivery preferences), **Inventory Status** legend (preview — "All items will be validated in next step"), **Fraud Check** preview ("will be performed after order review").

**4. Step 2 — Products**: product search grid with Add buttons (disabled once out of stock or already in the cart), and an Order Items table (qty stepper, per-line inventory status badge, line total, remove). Totals recompute live in the sidebar on every add/remove/qty change.

**5. Step 3 — Shipping**: radio-card list of shipping methods (carrier, ETA, price) plus a free-text Delivery Instructions field.

**6. Step 4 — Payment**: radio-card list of payment methods (Card, Cash, Bank Transfer, Pay Later/Net Terms, Split Payment) with an "Amount due" readout. Selecting Card reveals card-detail fields; selecting Split reveals a two-method allocation UI.

**7. Step 5 — Review & Confirm**: read-only recap of every prior step (Customer, Products, Shipping, Payment), each with an **Edit** link that jumps straight back to that step, plus a computed **Fraud Check** result (Low/Medium/High with the specific reasons — see Business rules).

**8. Order Summary sidebar** (persists across all 5 steps): Items Total, Discount, Shipping, Tax, Grand Total, Total Savings — all recomputed live from wizard state, never stale between steps.

**9. Apply Coupon** (sidebar): code input → validated against expiry/usage-limit → success state with a Remove (×) action, or an inline error.

**10. Quick Actions** (sidebar): Add Custom Product (jumps to Step 2), Apply Discount, Add Gift Card, Internal Note (jumps to Step 1). *Apply Discount and Add Gift Card are recognized clicks in v1 but don't yet open a dedicated modal — see Edge cases.*

**11. AI Assistant panel** (sidebar, persistent): capability list — Recommend products, Suggest upsells, Suggest cross-sells, Apply best discount, Check customer history, Detect duplicate orders, Recommend shipping method — plus an "Ask AI Assistant" entry point (same conversational surface as the top-bar/Dashboard assistant, Vol 2.1 §3.8/13).

## Fields
See Layout above for the full per-step field list. Cross-step state held by the wizard: customer selection/new-customer form, billing/shipping addresses, sales channel/warehouse/currency/priority, tags, internal notes, line items (product + qty), shipping method + delivery instructions, payment method, applied coupon.

## Workflows
1. **Phone order (existing customer)**: Sales rep searches the caller by phone → customer card confirms identity + outstanding balance → addresses auto-populate from the customer record → adds products the caller wants → picks Express Shipping → takes payment over the phone (Card) → reviews → Create Order.
2. **Walk-in / new customer**: Staff selects New Customer → fills first/last/email/phone → proceeds without a billing history (Customer Recent Orders/Notes cards are omitted for new customers, since there's no history yet) → completes the order.
3. **Draft-then-resume**: Rep starts an order, isn't ready to finalize payment, clicks Save Draft → order is created with `status: draft` and **no inventory reservation** (see Business rules) → resumed later from Screen 2.2.7 (Draft Orders, not yet built).
4. **Coupon-assisted order**: Rep applies a known promo code in the sidebar at any step → discount and tax recompute immediately → visible on Review before confirming.
5. **Fraud-flagged order**: Review step computes High Risk (e.g., new/unregistered customer + high order value) → rep can still proceed (fraud check is advisory in this wizard, not a hard block) but the flag is visible before commit, and a real fraud-check API call happens post-creation per Business rules.

## Business rules
- Customer must be selected (existing) or entered (new) before Products becomes reachable — products cannot be added without a valid customer context.
- Inventory is checked before confirmation (Step 5's fraud/inventory-adjacent visibility), but the *reservation itself* only happens on confirm, not on add-to-cart.
- Coupon validation (expiry, usage limit, customer eligibility) occurs before final pricing is shown on Review — an expired or exhausted code is rejected inline at Apply-time, not silently accepted and caught later.
- Taxes are calculated based on the shipping destination (this wizard uses a flat demo rate; Volume 12 Finance owns the real jurisdiction-aware tax engine).
- Fraud analysis runs before the order is confirmed — the Review step's computed risk badge is the UI preview of the real `POST /fraud/check` call that fires on submission.
- **Draft orders do not reserve inventory. Confirmed orders reserve inventory automatically.** This is the one rule most likely to surprise a new implementer: a Draft with 5 units of a nearly-sold-out SKU does not protect those units from being sold to someone else.

## Validation
Existing-customer flow blocks Next Step on Step 1 until a customer is selected; new-customer flow requires Email at minimum. Step 2 blocks Next Step until ≥1 line item exists. Step 4 blocks Next Step until a payment method is chosen. Internal Notes hard-caps at 500 characters (enforced by truncating input, not just a counter warning).

## Notifications
Order created confirmation to the customer (email/SMS per their preference — module-wide, Vol 2.2 README); Draft saved confirmation to staff; High Risk fraud flag surfaced inline on Review (not a separate notification — it's blocking-visible before the confirm click, which is stronger than a dismissible toast).

## Audit logs
`order.created` (via this screen, tagged `source: manual_admin`), `order.draft_saved`, `order.fraud_check_run` (result + reasons), `customer.created` (if New Customer was used), `discount.redeemed` (if a coupon was applied) — all per the module-wide audit spec (Vol 2.2 README).

## Database schema
Writes to the module-wide `orders`/`order_items`/`order_addresses`/`order_discounts`/`order_taxes` tables (Vol 2.2 README) plus:
```
draft_orders(id, store_id, customer_id null, line_items jsonb, addresses jsonb,
             settings jsonb, created_by, created_at, updated_at)
order_shipping(id, order_id, method_id, carrier, price, delivery_instructions)
order_notes(id, order_id, body, type[internal], author_id, created_at)   -- shared with Vol 2.2.1
order_tags(order_id, tag)                                                -- shared with Vol 2.2.1
fraud_checks(id, order_id, risk_level, reasons jsonb, checked_at)
inventory_reservations(id, order_id, product_variant_id, qty, reserved_at, released_at null)
```

## APIs
`GET /api/v1/customers/search`, `POST /api/v1/customers`, `GET /api/v1/products/search`, `POST /api/v1/orders/draft`, `POST /api/v1/orders`, `GET /api/v1/shipping/methods`, `GET /api/v1/tax/calculate`, `POST /api/v1/discount/apply`, `POST /api/v1/fraud/check`, `GET /api/v1/warehouses`.

## Events
`order.created`, `order.draft_saved`, `order.fraud_flagged`, `customer.created`, `inventory.reserved` — consumed by Orders Dashboard (Vol 2.2.1, new row appears immediately), Inventory (Vol 9), Finance (Vol 12, for payment capture on Card/Cash).

## Edge cases
- New customer with no order history: Customer Recent Orders / Customer Notes cards are omitted entirely on Step 1 rather than shown empty, since there's genuinely nothing to show yet.
- Product goes out of stock between Step 2 add and Step 5 confirm (another order took the last unit): the real system re-validates inventory at confirm time and blocks with a clear message; this wizard's mock data is static so the scenario can't reproduce, but the Business rule (reservation only on confirm) exists specifically to make this race condition survivable rather than silently overselling.
- Split Payment where the two allocated amounts don't sum to the grand total: real implementation blocks Create Order until they reconcile; v1 UI collects the two amounts but doesn't yet cross-validate the sum — tracked as a gap.
- **Known v1 gap**: Apply Discount and Add Gift Card quick actions register the click (visible affordance) but don't yet open a dedicated modal — Apply Coupon in the sidebar is the only *functional* discount path today.
- **Known v1 gap**: address editing is read/select-only — "Edit" and "Add New Address" are present but non-functional; full address CRUD is scoped to Screen 2.2.3 (Order Details) and Customers (Vol 2.4), not duplicated here.
- Customer with an outstanding balance selects Pay Later (Net Terms): should be blocked or require override per their credit limit (Vol 2.13 B2B) — not yet enforced in this wizard, flagged for the Volume 2.13 cross-link.

## Error handling
Coupon apply failure (not found / usage limit reached) → inline error message under the input, coupon state unchanged, no silent no-op. Save Draft failure → wizard state is preserved client-side (nothing is lost) with a retry prompt, since losing an in-progress manual order is the single worst failure mode for this screen.

## Performance
Customer and product search are typeahead-shaped but currently filter the small in-memory mock list; the real implementation debounces `GET /customers/search` / `GET /products/search` server-side. Order Summary recomputation is pure client-side arithmetic on wizard state — no network round-trip per keystroke/qty-change.

## Security
Card Details fields in Step 4 are UI-only in this reference build (no real tokenization) — production must route these through a PCI-scope payment provider (Volume 12 Finance) and never let raw card data touch CommerceOS's own servers. Fraud check results and reasons are logged per Audit logs above. Customer PII shown in the customer card (email, phone, outstanding balance) is subject to the same field-level access logging as Volume 2.4 Customers.

## AI opportunities
The 7 listed capabilities (§ AI Assistant panel) are the v1 surface. Beyond that: auto-fill Step 1 from a phone-number caller-ID match; AI-suggested shipping method based on customer history (e.g., "this customer always picks Express"); proactive duplicate-order detection running continuously as items are added, not only at Review; AI-drafted internal note summarizing anything unusual about this order for the next staff member who opens it.

## UX improvements
Persisting an in-progress (unsaved) order to local storage so an accidental tab close doesn't lose work; keyboard shortcuts to jump between steps; a compact "order so far" ticker visible even while scrolled deep into a step's content (today the sidebar requires no scroll to stay visible, but a very long product list could push it below the fold on short viewports).

## Estimated scope (this screen)
5 wizard steps, 4 sidebar panels (Summary, Coupon, Quick Actions, AI Assistant), ~10 API endpoints, 6 additional/shared DB tables, 6-role permission matrix, ~8 documented edge cases.

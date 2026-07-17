# 2.6 Discounts

## Purpose
Create and manage promotional pricing: code-based discounts, automatic discounts, and bundles — applied at cart/checkout across all sales channels consistently.

## Navigation
Sidebar `Discounts`. Sub-tabs: All Discounts, Automatic Discounts, Bundles. Create/edit is a dedicated route with a live preview of the discount summary.

## User roles
Owner/Manager: full CRUD. Marketing: full CRUD within an Owner-configured max discount ceiling (e.g., cannot create >50% off without approval). Support: view-only (to explain discounts to customers), can apply a one-off manual discount to a specific order (separate permission).

## Permissions
`discounts.view`, `discounts.create`, `discounts.edit`, `discounts.delete`, `discounts.exceed_ceiling` (Owner-only by default).

## Fields
Title/code, type (Percentage/Fixed amount/Free shipping/Buy X Get Y), value, applies to (all products/specific collections/specific products), minimum requirements (min purchase amount or min quantity), customer eligibility (all/specific segment/specific customers), usage limits (total uses, one per customer), combinability (stackable with other discounts: yes/no, and with which types), active dates (start/end), status.

## Buttons
Create discount, Duplicate, Deactivate/Activate, Delete, Generate random code, Bulk-generate unique codes (for influencer/affiliate use), Preview cart impact.

## Tables
List: title/code, type, value, status, used count / usage limit, active dates.

## Filters
Type, status (Active/Scheduled/Expired), combinability.

## Search
Code/title.

## Bulk actions
Bulk activate/deactivate, bulk delete (unused only), bulk export usage report.

## Workflows
1. Create discount → define rules/eligibility/combinability → activate immediately or schedule → propagates to all channels via cache invalidation.
2. Customer applies code at checkout → real-time validation (eligibility, usage limit, min purchase) → applied atomically with order creation to prevent race conditions on limited-use codes.
3. Bulk unique-code generation for an affiliate program → export list → distribute externally → usage tracked per code back to this discount record.

## Business rules
- Usage limit enforcement must be atomic (row-level lock or optimistic concurrency) to prevent over-redemption under concurrent checkouts of a limited-quantity code.
- Combinability: a discount marked non-combinable overrides any other discount's combinability setting when both would otherwise apply — the more restrictive rule always wins.
- Buy X Get Y bundles require the "get" item to be in stock and available in the same channel as the order; otherwise the offer is not shown/applied.
- Percentage discounts cannot exceed 100%; fixed-amount discounts cannot reduce a line below $0.

## Validation
Code uniqueness (case-insensitive) within store; end date > start date; at least one "applies to" scope selected; numeric value > 0.

## Notifications
Discount expiring soon (staff reminder), usage limit nearly reached, discount auto-deactivated on expiry.

## Audit logs
`discount.created/edited/deleted/activated/deactivated`, `discount.redeemed` (linked to order, for fraud/usage analysis).

## Database schema
```
discounts(id, store_id, title, code, type, value, applies_to jsonb, min_requirement jsonb,
          customer_eligibility jsonb, usage_limit, per_customer_limit, combinable_with jsonb,
          starts_at, ends_at, status, created_at, updated_at)
discount_redemptions(id, discount_id, order_id, customer_id, amount_applied, redeemed_at)
```

## APIs
`GET/POST /api/v1/discounts`, `GET/PATCH/DELETE /api/v1/discounts/{id}`, `POST /api/v1/discounts/validate` (checkout-time eligibility check), `GET /api/v1/discounts/{id}/redemptions`.

## Events
`discount.created`, `discount.redeemed`, `discount.expired`, `discount.usage_limit_reached` — consumed by Orders (discount application), Analytics, Dashboard.

## Edge cases
Two customers redeem the last unit of a limited-use code simultaneously (only one should succeed — requires transactional check at order-creation, not just at cart-display); discount referencing a since-deleted product/collection (gracefully degrade, exclude from calculation, alert merchant); discount code that collides with a since-deleted code's old value (block reuse for a cooldown period or allow — configurable).

## Error handling
Discount validation API failure at checkout → fail closed (don't apply discount, don't block checkout) with customer-facing "code could not be validated, try again" rather than silently dropping the discount.

## Performance
Discount validation must respond within checkout SLA (<150ms) — eligibility rules pre-compiled/cached, not evaluated against raw JSON on every request.

## Security
Rate limiting on discount code guessing at checkout (prevent brute-forcing valid codes); redemption writes are transactional to prevent limit bypass via concurrent requests.

## AI opportunities
AI-suggested discount depth/timing based on inventory aging and margin targets; predicted incremental revenue vs. margin erosion before activating; auto-flag likely discount abuse patterns (same customer, multiple accounts).

## UX improvements
Live preview showing exactly how the discount affects a sample cart; conflict warnings when creating a discount that overlaps confusingly with an existing one; calendar view of scheduled discounts.

## Estimated scope
~5 sub-views, ~6 API endpoints, 2 DB tables, ~25 functional requirements.

# 2.3.1 Product Management Dashboard

Reference implementation: `/web/src/app/products/page.tsx` + `/web/src/components/products/*` + `/web/src/lib/products-data.ts`.

Status: ✅ Built. Manage the complete product catalog — pricing, inventory, variants, media, SEO, publishing, and performance — from one screen, following the same list + inline-detail-panel + right-sidebar pattern established by Orders (Screen 2.2.1).

## Purpose
Give staff a single screen to find any product, understand its catalog/inventory/pricing state at a glance, and act on it (edit, publish, archive, adjust inventory) or drill into full multi-tab detail without leaving the page.

## Navigation
- Route `/products`, sidebar item `Products`.
- Breadcrumb: `Dashboard > Products`.
- Clicking a product's name or the row's eye icon loads it into the inline **Product Detail Panel** at the bottom of the screen (10 tabs) rather than navigating away — the full-page Product Details route (Screen 3.3) is the deeper view for when inline isn't enough.

## User roles & Permissions
Inherits the module-wide permission matrix from the [Products README](./README.md#user-roles--permissions-matrix). Screen-specific: `products.export` gates Export; `products.import` gates Import; `products.publish` gates the Publish/Unpublish bulk actions and the Sales Channels publish toggles in the detail panel; `products.edit_cost` independently gates the Cost Price / Profit Margin rows in the Pricing tab (rendered but redacted for roles lacking the grant).

## Layout

**1. Header** — breadcrumb, page title, Export (Excel/CSV/JSON/XML), Import (CSV/Excel/Shopify/WooCommerce/Magento/API), Add Product (dropdown: Simple/Variable/Digital/Bundle/Subscription/Gift Card/Service Product — each routes to Screen 3.2's wizard, pre-selecting the type).

**2. KPI cards (5)** — Total Products, Active Products, Out of Stock, Low Stock, Total Value. Each expands an inline breakdown popover:
- Total Products → Today's added / This month / Growth %
- Active Products → Published / Draft / Archived
- Out of Stock → Out of stock / Need purchase / Critical products
- Low Stock → Low inventory / Warning products / Forecasted shortage
- Total Value → Cost value / Selling value / Profit margin

**3. Search** — single input across Product Name, SKU, Barcode, Brand, Vendor, Collection, Tag, Category (implemented as one input matching across indexed fields; real-time autocomplete is the next increment — v1 filters on submit/keystroke against the loaded page, not a typeahead dropdown).

**4. Filters** — Status, Brand, Vendor, Collection, Category, Product Type, Sales Channel, Price, Inventory, Created Date, Updated Date, Published, Tags. Same v1 scope note as Orders (Vol 2.2.1): the filter group list renders; per-group value pickers are the next increment.

**5. Columns** — functional show/hide. Always-on: Product, SKU, Actions. Toggleable: Category, Price, Stock, Status, Type, Sales Channel, Created Date, Updated Date.

**6. Sort** — Date (Newest/Oldest), Price (High→Low/Low→High), Stock (High→Low), Name (A–Z).

**7. Bulk actions** — enabled only when ≥1 row is selected: Publish, Unpublish, Archive, Delete, Change Category, Change Brand, Update Tags, Update Prices, Inventory Adjustment, Assign Collections, Export, **Generate AI Description**. Destructive (Delete) renders in red.

**8. Product tabs** — All, Active, Draft, Out of Stock, Low Stock, Discontinued, Archived — each with a live count; selecting one filters the table by the product's status bucket.

**9. Product table** — checkbox, thumbnail + name + variant, SKU, [toggleable columns], Sales Channel icons (+N overflow), Actions. Row actions: Eye (view → loads detail panel), Pencil (edit), `⋮` menu with Duplicate, Manage Inventory, Analytics, Archive, Delete. Status and Type render as color-coded badges. Stock number is color-coded (red at 0, amber at/below threshold, green otherwise) so risk is visible without reading the Status badge. Footer: "Showing X to Y of Z products" + pagination.

**10. Product Detail Panel** (inline, loads the selected product): header (title, SKU, status badge, View Product, More actions) + **10 tabs** — Overview, Variants, Inventory, Pricing, Media, SEO, Attributes, Sales, Activity, AI Insights:
- **Overview** — four columns: Product Information (name, SKU, barcode, category, brand, type, status, created/updated), Pricing (price, compare-at, cost, margin, currency, tax class), Inventory (quantity, reserved, available, warehouse, stock status, low-stock threshold), Sales Channels (per-channel Published/Hidden/Pending Approval badges).
- **Variants** — table of this product's variants (name, SKU, price, stock, status).
- **Inventory** — quantity/reserved/available/warehouse/threshold/policy in a focused view (same data as the Overview card, for when inventory is the whole reason staff opened the panel).
- **Pricing** — price/compare-at/cost/margin/currency/tax class in a focused view.
- **Media** — asset grid (this product's images).
- **SEO** — editable SEO title, meta description, URL handle, keyword chips.
- **Attributes** — key/value spec list (Color, Connectivity, Battery Life, etc.).
- **Sales** — units sold, revenue, conversion rate, return rate (30-day).
- **Activity** — chronological change log (price changes, restocks, publishes, AI actions) with actor + timestamp.
- **AI Insights** — product-specific AI findings (stock risk, declining sales, SEO gaps, missing images, pricing inconsistency) plus a **Generate AI Description** action.

**11. Right sidebar** — Quick Actions (Add Product, Import Products, Export Products, Bulk Edit, Categories, Brands, Attributes, Reviews, Trash), Product Status legend (Active/Draft/Out of Stock/Low Stock/Discontinued/Archived, color-coded), Top Categories (with counts, click-through to category filter), and a dismissible **AI Insights** card (store-wide, distinct from the per-product AI Insights tab) surfacing e.g. "12 products are low in stock," "3 products need SEO improvement."

## Fields
Product: id, name, variant label, SKU, barcode, category, brand, vendor, price, compare-at price, cost price, currency, tax class, stock, reserved, warehouse, low-stock threshold, status (derived — see Business rules), type, channels, created/updated timestamps, status-bucket membership.

## Workflows
1. **Triage**: staff lands on All → scans KPI deltas → clicks Low Stock tab → works down the list adjusting inventory via row `⋮` → Manage Inventory.
2. **Find and edit**: staff searches a SKU → clicks the eye icon → detail panel loads on Overview → switches to Pricing tab → notes the margin, switches to Activity to see price history context.
3. **Bulk merchandising**: staff filters to Draft → selects several rows → Bulk actions → Publish.
4. **AI-assisted content**: staff opens a product's AI Insights tab → sees "3 products have missing images" isn't about this product but the store-wide equivalent is visible in the right sidebar → clicks Generate AI Description on a product that needs one.
5. **Quick create**: staff clicks Add Product → picks a type (e.g. Variable Product) → routed to Screen 3.2 (not yet built) pre-configured for that type.

## Business rules
Inherits all module-wide rules from the [Products README](./README.md#business-rules). Screen-specific: the table's Status badge and the row's stock-number color both derive from the same stock-vs-threshold computation — they cannot disagree (single source of truth per row, not two separately-set fields).

## Validation
Search requires no minimum length; bulk action buttons disabled (not hidden) when selection is empty; column toggle always leaves Product/SKU/Actions visible.

## Notifications
Inherits module-wide (see README). Screen-specific: toast confirms bulk action completion with per-item success/failure breakdown (e.g., "8 published, 2 failed — missing required fields").

## Audit logs
Every row action and bulk action logs `product.<action>` per the module-wide audit spec, plus `products_dashboard.column_visibility_changed` and `products_dashboard.filter_applied` (UX analytics, lower retention).

## Database schema
Reads from the module-wide tables (see [Products README](./README.md#database-schema-module-wide)). Adds:
```
user_products_view_preferences(id, user_id, store_id, visible_columns jsonb,
                                default_sort text, default_tab text, updated_at)
```

## APIs
`GET /api/v1/products?bucket=&search=&sort=&page=` (paginated, server-side filtered), `GET /api/v1/products/kpis?range=`, plus the module-wide mutation endpoints (publish/archive/duplicate/bulk-update) invoked from row and bulk actions. `PUT /api/v1/products-dashboard/preferences` for column/sort persistence.

## Events
Consumes `product.created/updated/published/archived/deleted` and `inventory.level_changed` to keep KPI cards and tab counts live without a full page refresh (same targeted-invalidation pattern as Dashboard, Vol 2.1 §15, and Orders, Vol 2.2.1).

## Edge cases
- Zero products match the active tab+search combination → empty state with a "Clear filters" CTA.
- A product with variants has per-variant stock that disagrees with the parent's aggregate Status badge (e.g., one variant out of stock, others fine) → parent Status reflects the *worst* variant state, full detail visible in the Variants tab.
- User hides every optional column → table still shows Product/SKU/Actions.
- **Known v1 gap**: Filters button lists filter groups without per-group value pickers, same as Orders — functional filtering today is via Search + status tabs.
- **Known v1 gap**: pagination controls update `currentPage` state but the mock dataset only has 6 products, so pages 2+ render the same 6 rows — documented so it isn't mistaken for a bug during review.

## Error handling
Failed KPI fetch → per-card retry state (same error-boundary pattern as Dashboard). Failed bulk action → per-item success/failure breakdown in the toast rather than all-or-nothing. Failed AI description generation → inline retry in the AI Insights tab, no partial/garbled content ever saved to the product.

## Performance
Product list is server-side paginated and filtered — target p95 < 400ms for a page of 50. KPI cards read from a rollup, not computed live from `products`/`product_inventory` on every load. Thumbnail images served via CDN with responsive sizes (module-wide, see README Performance-adjacent Security note).

## Security
Inherits module-wide (cost/margin field-level gating, row-level `store_id` scoping). Column visibility and filter state are per-user.

## AI opportunities
The Generate AI Description bulk/row action and the AI Insights tab/sidebar are the v1 surface. Beyond that: AI-suggested pricing based on comparable catalog + market data; auto-tagging/categorization on import; duplicate/near-duplicate product detection; auto-generated alt text for every image in the Media tab; proactive "this SKU will stock out in N days" predictions feeding the Low Stock tab directly (not just the Dashboard widget).

## UX improvements
Saved filter+column+sort views as named presets; inline variant-matrix editing (spreadsheet-like) directly from the Variants tab instead of only via Screen 3.4; drag-and-drop media reordering in the Media tab; side-by-side channel preview before publish.

## Estimated scope (this screen)
5 KPI cards, 7 status tabs, 8 toggleable columns, 12 bulk actions, 8 row actions (2 direct + 6 in the `⋮` menu), 10-tab inline product detail, 4 right-sidebar widgets, ~4 screen-specific API endpoints (plus module-wide mutation endpoints), 1 additional DB table.

# 2.3 Products

System of record for the catalog: products, variants, pricing, media, inventory linkage, SEO, and publishing across every sales channel (storefront, POS, marketplace, social). Like Orders (Volume 2.2), Products is documented and built as a **multi-screen module** — 15 screens total.

## Screens

| # | Screen | Status | Notes |
|---|---|---|---|
| 3.1 | [Product Management Dashboard](./01-products-dashboard.md) | ✅ Built | List + inline detail panel — reference implementation at `/web/src/app/products/page.tsx` |
| 3.2 | Product Creation Wizard | ⬜ Not started | Guided multi-step create flow (the Dashboard's "Add Product" dropdown picks a type; this screen is the actual builder) |
| 3.3 | Product Details (full page) | ⬜ Not started | Dedicated `/products/{id}` route — the Dashboard's inline panel is the v1 preview of this |
| 3.4 | Product Variants | ⬜ Not started | Full variant matrix editor (options × values → SKUs) |
| 3.5 | Collections | ⬜ Not started | Manual and rule-based (smart) collections |
| 3.6 | Categories | ⬜ Not started | Hierarchical category tree management |
| 3.7 | Brands | ⬜ Not started | Brand directory, logos, vendor linkage |
| 3.8 | Inventory Management | ⬜ Not started | Deep per-location stock — cross-links Volume 9 |
| 3.9 | Media Library | ⬜ Not started | Store-wide asset library (not just per-product media) |
| 3.10 | SEO & Search Optimization | ⬜ Not started | Store-wide SEO tooling beyond the per-product SEO tab |
| 3.11 | Reviews & Ratings | ⬜ Not started | Customer review moderation |
| 3.12 | Product Analytics | ⬜ Not started | Deep per-product performance — cross-links Volume 2.7 |
| 3.13 | Bulk Product Operations | ⬜ Not started | Job status/history for bulk actions triggered from 3.1 |
| 3.14 | Product Import/Export | ⬜ Not started | Job history/mapping UI behind the Dashboard's Import/Export buttons |
| 3.15 | Product Settings | ⬜ Not started | Default inventory policy, SKU format, weight units, tax defaults |

## Cross-cutting rules (apply across all 15 screens)

### User roles & Permissions matrix
| Permission | Owner | Admin | Manager | Inventory | Marketing | Read Only |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| View Products | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create Products | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit Products | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Delete Products | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Publish Products | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Bulk Update | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Export Products | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Permission keys: `products.view`, `products.create`, `products.edit`, `products.delete`, `products.publish`, `products.bulk_update`, `products.export`, `products.edit_cost` (separate from `products.edit_price` — cost/margin is more sensitive than price and independently gated even for roles that can edit price), `products.import`.

### Business rules
- A product with variants must have ≥1 variant; deleting the last variant is blocked (delete the product instead).
- SKU must be unique per store; barcode uniqueness is a soft warning, not a hard block.
- Compare-at price must be > price if set, to represent a genuine discount rather than a fake markup (flagged if violated, per marketing-claims compliance).
- Archiving a product removes it from active sales channels but preserves historical order line item references.
- Cost field is only visible/editable to roles with `products.edit_cost`; it drives Dashboard Net Profit (Vol 2.1) and Analytics margin reports, and is never exposed via the same field-level check as price.
- Stock Status (Active/Out of Stock/Low Stock shown as the product's overall "Status" badge) is derived, not manually set: Out of Stock = stock 0, Low Stock = stock ≤ low_stock_threshold, otherwise Active — mirrors the Inventory Alerts logic in Dashboard Vol 2.1 §6.

### Notifications
Low-stock threshold crossed (routes to Dashboard/Inventory alerts, Vol 2.1), import job completed/failed, bulk price/inventory update completed, product publish scheduled reminder, AI-generated insight surfaced (declining sales, missing images, inconsistent pricing).

### Audit logs
`product.created/updated/deleted/archived/published`, `product.price_changed` (before/after), `product.bulk_edit` (job id, affected count, actor), `product.ai_description_generated`.

### Database schema (module-wide)
```
products(id, store_id, title, description, status, product_type, vendor, brand_id,
         seo_title, seo_description, handle, created_at, updated_at)
product_variants(id, product_id, sku, barcode, price, compare_at_price, cost,
                  weight, requires_shipping, track_inventory, position)
product_options(id, product_id, name, position)
product_option_values(id, option_id, value, position)
product_variant_option_values(variant_id, option_value_id)
product_images(id, product_id, url, alt_text, position, type[image|video])
product_media(id, product_id, asset_id, position)         -- links to a store-wide media library (Screen 3.9)
product_inventory(id, product_variant_id, location_id, quantity, reserved, low_stock_threshold)
product_prices(id, product_variant_id, currency, price, compare_at_price)  -- multi-currency, Vol 2.11
product_categories(product_id, category_id)
product_brands(id, store_id, name, logo_url)
product_attributes(id, product_id, label, value)
product_tags(product_id, tag)
product_reviews(id, product_id, customer_id, rating, body, status, created_at)
product_sales_channels(product_id, channel_id, status[published|hidden|pending_approval])
product_activity_logs(id, product_id, actor_id, action, before jsonb, after jsonb, created_at)
product_ai_insights(id, product_id, type, message, tone, generated_at, dismissed_at)
```

### APIs (module-wide)
`GET/POST /api/v1/products`, `GET/PATCH/DELETE /api/v1/products/{id}`, `POST /api/v1/products/{id}/publish`, `POST /api/v1/products/{id}/archive`, `POST /api/v1/products/{id}/duplicate`, `POST /api/v1/products/import`, `GET /api/v1/products/export`, `POST /api/v1/products/bulk-update`. Webhooks: `products/create`, `products/update`, `products/delete`.

### Events
`product.created`, `product.updated`, `product.price_changed`, `product.published`, `product.archived`, `product.deleted` — consumed by Storefront (cache invalidation), Inventory (Vol 9), Analytics (Vol 2.7), Marketplace listings (Vol 6), Dashboard (Vol 2.1 Inventory Alerts).

### Security
Cost/margin fields access-controlled independently from price (see Business rules); import files scanned for malformed/malicious content before processing; product media served from a sandboxed storage domain (no script execution risk); AI-generated content (descriptions, SEO) is logged with the generating prompt for review before publish.

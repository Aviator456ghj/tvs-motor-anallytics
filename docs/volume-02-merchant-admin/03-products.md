# 2.3 Products

## Purpose
System of record for the catalog: products, variants, pricing, media, and their linkage to inventory. Everything sold anywhere (storefront, POS, marketplace, social channels) originates here.

## Navigation
Sidebar `Products`. Sub-tabs: All Products, Collections, Inventory (deep link to Volume 9), Categories, Attributes/Options, Import/Export. Product detail is its own route (`/products/{id}`) with tabs: Details, Variants, Media, SEO, Organization.

## User roles
Owner/Manager: full CRUD. Merchandiser (Staff subtype): create/edit, no delete/publish without approval (configurable). Marketing: edit SEO/content fields only. Finance: read-only, cost field visibility gated separately.

## Permissions
`products.view`, `products.create`, `products.edit`, `products.delete`, `products.publish`, `products.edit_cost` (separate from `products.edit_price` — cost is margin-sensitive), `products.import_export`.

## Fields
Title, description (rich text), status (Draft/Active/Archived), product type, vendor, tags, collections, options (e.g., Size/Color) and their values, variants (SKU, barcode, price, compare-at price, cost, weight, inventory tracking on/off), media (images/video, alt text, sort order), SEO title/description/handle, categorization, shipping (weight, dims, requires-shipping toggle), tax code/category.

## Buttons
Save, Save & publish, Duplicate, Archive, Delete, Preview on storefront, Add variant, Bulk edit variants, Import (CSV), Export (CSV), Generate with AI (description/title/tags), Add to collection.

## Tables
Product list: thumbnail, title, status, inventory (across locations), type, vendor, price range (if variants), channels published to. Variants table within product detail: image, SKU, price, cost, inventory, weight.

## Filters
Status, vendor, product type, collection, tag, channel availability, inventory level (in stock/low/out), price range.

## Search
Title, SKU, barcode, vendor, tag — typeahead with thumbnail preview.

## Bulk actions
Bulk status change, bulk tag/untag, bulk add to collection, bulk price adjustment (% or fixed, with preview before apply), bulk delete/archive, bulk export.

## Workflows
1. Create product → set options/variants → upload media → set pricing/inventory per location → Save as Draft or Publish directly to selected channels.
2. Import via CSV → validation report (row-level errors) → confirm → async job creates/updates products → completion notification with error log download.
3. Price change → optional scheduling (effective date) → propagates to all channels via `product.updated` event.

## Business rules
- A product with variants must have ≥1 variant; deleting the last variant is blocked (delete the product instead).
- SKU must be unique per store (not per-variant-globally); barcode uniqueness is a soft warning, not hard block.
- Compare-at price must be > price if set (to represent a genuine discount, not a fake markup — flagged if violated per compliance).
- Archiving a product removes it from active channels but preserves historical order line item references.
- Cost field only visible/editable to roles with `products.edit_cost`; drives Dashboard Net Profit (Vol 2.1) and Analytics margin reports.

## Validation
Required: title, ≥1 variant with price ≥ 0. Price precision to currency's minor unit. Weight required if `requires_shipping` true. Media: max file size/type enforced client + server side.

## Notifications
Low-stock threshold crossed (routes to Dashboard/Inventory alerts), import job completed/failed, bulk price update completed, product publish scheduled reminder.

## Audit logs
`product.created/updated/deleted/archived/published`, `product.price_changed` (before/after), `product.bulk_edit` (job id, affected count, actor).

## Database schema
```
products(id, store_id, title, description, status, product_type, vendor, seo_title,
         seo_description, handle, created_at, updated_at)
product_options(id, product_id, name, position)
product_option_values(id, option_id, value, position)
product_variants(id, product_id, sku, barcode, price, compare_at_price, cost,
                  weight, requires_shipping, track_inventory, position)
product_variant_option_values(variant_id, option_value_id)
product_media(id, product_id, url, alt_text, position, type[image|video])
product_collections(product_id, collection_id)
product_tags(product_id, tag)
```
(Inventory levels/locations live in Volume 9; referenced by `product_variant_id`.)

## APIs
`GET/POST /api/v1/products`, `GET/PATCH/DELETE /api/v1/products/{id}`, `POST /api/v1/products/{id}/publish`, `POST /api/v1/products/import`, `GET /api/v1/products/export`, `POST /api/v1/products/bulk`. Webhooks: `products/create`, `products/update`, `products/delete`.

## Events
`product.created`, `product.updated`, `product.price_changed`, `product.published`, `product.archived`, `product.deleted` — consumed by Storefront cache invalidation, Inventory, Analytics, Marketplace listings (Vol 6).

## Edge cases
Product with 0 variants (draft state, blocked from publish); duplicate SKU on import (row rejected, rest proceed); media upload failure mid-batch (partial success reported); product referenced by an active discount/bundle being deleted (soft-block with warning); currency-specific pricing when Markets (Vol 2.11) has multiple currencies active.

## Error handling
CSV import row failures collected and returned as a downloadable error report rather than failing the whole batch. Media upload retries with exponential backoff; permanent failure surfaces per-file error in the media grid.

## Performance
Product list virtualized/paginated for catalogs >10k SKUs; image thumbnails served via CDN with responsive sizes; bulk operations run as async jobs with progress polling, never synchronous for >100 items.

## Security
Cost/margin fields access-controlled independently from price; import files scanned for malformed/malicious content; product media served from sandboxed storage domain (no script execution risk).

## AI opportunities
AI-generated titles/descriptions/SEO from a few input attributes or a photo; auto-tagging and categorization; duplicate/near-duplicate product detection on import; AI-suggested pricing based on comparable catalog + market data; auto-generated alt text for accessibility.

## UX improvements
Drag-and-drop media reordering; inline variant matrix editing (spreadsheet-like); side-by-side channel preview before publish; undo for bulk edits within a time window.

## Estimated scope
~10 sub-views, ~10 API endpoints, 7 DB tables, ~45 functional requirements.

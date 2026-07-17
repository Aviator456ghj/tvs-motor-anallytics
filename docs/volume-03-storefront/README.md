# Volume 3 — Storefront

Status: ⬜ Not started (skeleton).

The customer-facing, themed shopping experience — everything an end customer sees before/during purchase. Consumes the catalog from Volume 2 (Products), pricing from Volume 2 (Markets), and inventory from Volume 9.

## Planned modules/pages
- Home / landing page (theme sections, hero, featured collections)
- Collection / category (PLP) — grid, filters, sort, faceted search
- Product detail page (PDP) — variants, media gallery, reviews, upsell/cross-sell, AI shopping assistant widget
- Search & discovery (autocomplete, AI-powered semantic search)
- Cart (drawer + full page)
- Checkout (address, shipping method, payment, order review) — one-page and multi-step variants
- Order confirmation / thank-you page
- Theme editor (merchant-facing, drag-and-drop section/block builder — cross-links Volume 18 UI Design System)
- Headless/composable storefront option (API-first, for custom frontends — cross-links Volume 15 APIs)

## Dependencies
Products & Markets (Vol 2), Inventory (Vol 9), OMS (Vol 7) for checkout→order handoff, Discounts (Vol 2.6) for cart pricing, AI Platform (Vol 13) for search/recommendations/shopping assistant.

## Next steps
Author each page to the full CommerceOS template (Purpose → UX improvements), starting with PDP and Checkout as the highest-leverage conversion surfaces.

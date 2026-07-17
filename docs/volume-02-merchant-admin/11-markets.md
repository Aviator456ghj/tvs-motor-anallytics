# 2.11 Markets

## Purpose
Configure how the store sells into different countries/regions: currencies, languages, region-specific pricing, and localized checkout — enabling one catalog to serve a global customer base correctly.

## Navigation
Sidebar `Markets`. Sub-tabs: Markets (list of configured regions), Currencies, Languages, Pricing (region-specific overrides), Duties & Import Taxes.

## User roles
Owner/Manager: full access. Finance: view + currency/pricing (no new-market creation). Marketing: view-only (for localized campaign planning).

## Permissions
`markets.view`, `markets.create`, `markets.edit`, `markets.manage_currency`, `markets.manage_pricing`.

## Fields
Market: name, countries/regions included, status (Active/Draft), currency, language(s), domain/subdomain or path strategy (e.g., `/fr`, `fr.store.com`), pricing strategy (auto FX-converted vs. manual per-market prices), duties/tax handling (DDP/DDU).

## Buttons
Add market, Activate/Deactivate, Set currency, Add manual price override, Configure domain routing, Preview storefront in market.

## Tables
Markets list: name, countries, currency, status, % of traffic/revenue. Pricing override table: product, base price, market-specific price.

## Filters
Status, region/continent.

## Search
Market name, country.

## Bulk actions
Bulk price override import (CSV) for a market, bulk-add countries to a market.

## Workflows
1. Create market → select countries → assign currency + language → choose pricing strategy → activate → storefront begins serving localized experience for matched visitors (by domain, geo-IP, or language preference).
2. Manual pricing override: merchant sets specific prices per market instead of relying on live FX conversion, to avoid awkward price points (e.g., localize to .99 endings).
3. Duties configuration: merchant chooses DDP (duties paid at checkout, shown to customer) vs. DDU (paid on delivery) per market — affects checkout copy and Finance's tax/duty ledger entries.

## Business rules
- A country can only belong to one active market at a time (no ambiguity in which pricing/currency applies).
- If auto FX-converted pricing is used, rates refresh on a defined interval (e.g., daily) — prices do not fluctuate intra-day to avoid customer confusion/cart-price mismatches.
- Manual price overrides always take precedence over auto-converted prices for that specific product+market combination.
- Deactivating a market does not cancel in-flight orders already placed from that market; it only stops new checkout eligibility.

## Validation
Market must include ≥1 country; currency must be a supported ISO 4217 code; manual price override must be > 0.

## Notifications
FX rate moved significantly (threshold-based alert since it affects auto-converted margins), market activated/deactivated, pricing override import completed.

## Audit logs
`market.created/activated/deactivated`, `market.pricing_strategy_changed`, `market.price_override_changed`.

## Database schema
```
markets(id, store_id, name, status, currency, pricing_strategy, duty_handling, created_at)
market_countries(market_id, country_code)
market_languages(market_id, language_code, is_default)
market_price_overrides(id, market_id, product_variant_id, price)
fx_rates(base_currency, quote_currency, rate, as_of)
```

## APIs
`GET/POST /api/v1/markets`, `GET/PATCH/DELETE /api/v1/markets/{id}`, `POST /api/v1/markets/{id}/price-overrides`, `GET /api/v1/markets/{id}/preview`.

## Events
`market.activated`, `market.deactivated`, `market.pricing_changed`, `fx_rate.updated` — consumed by Storefront (pricing display), Orders (currency snapshot at purchase), Finance (multi-currency ledger).

## Edge cases
Visitor's geo-IP doesn't match any configured market (fallback to default/primary market); country reassigned from one market to another (existing customers mid-session see a currency-change prompt, not a silent switch); FX provider outage (fall back to last-known rate with a staleness flag, never block checkout).

## Error handling
Price override import with invalid product references → row-level error report, valid rows still applied; FX rate fetch failure → use last cached rate, alert Finance if staleness exceeds a threshold.

## Performance
Market/pricing resolution for a given visitor must be fast (<20ms) since it runs on every storefront page view; FX rates cached, not fetched live per request.

## Security
Pricing override changes audited (margin-sensitive); market/currency configuration changes require `markets.manage_currency` specifically, separate from general market view.

## AI opportunities
AI-recommended new markets based on existing organic traffic/demand signals; AI-suggested localized price points (psychological pricing per region); anomaly detection on FX-driven margin compression.

## UX improvements
Visual world-map market configuration; side-by-side storefront preview across markets; bulk price-override wizard with markup/markdown percentage input instead of manual per-SKU entry.

## Estimated scope
~5 sub-views, ~7 API endpoints, 5 DB tables, ~25 functional requirements.

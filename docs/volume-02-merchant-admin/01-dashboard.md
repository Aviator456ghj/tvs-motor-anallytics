# 2.1 Dashboard

Reference implementation: `/web/src/app/page.tsx` + `/web/src/components/dashboard/*`.

## Purpose
The Dashboard is the merchant's daily command center: a single screen answering "how is my store doing right now, and what needs my attention today?" It surfaces revenue/traffic KPIs, actionable tasks, at-risk inventory, and a conversational AI entry point, so an Owner can triage the business in under a minute without navigating to individual modules.

## Navigation
- Default landing page after login (route `/`).
- Sidebar item: `Dashboard` (icon: layout-dashboard), always first, no badge.
- Breadcrumb: none (root page).
- Date range selector (top-right, e.g. "May 10 – May 16, 2025") scopes every KPI/chart on the page.

## User roles
| Role | Access |
|---|---|
| Owner | Full view; can customize layout |
| Manager | Full view; can customize layout |
| Staff | View only widgets matching their granted module permissions (e.g., Finance-restricted staff don't see Net Profit) |
| Finance | Full KPI + Finance-adjacent widgets; Marketing widgets hidden |
| Marketing | Marketing Performance, Sales Overview, Customer Insights; Finance/Net Profit hidden |
| App/API | No UI access; equivalent data available via `/api/v1/analytics/summary` |

## Permissions
- `dashboard.view` — required to load the page at all.
- `dashboard.customize` — required to reorder/hide widgets (persisted per-user).
- Widget-level visibility is derived from the viewer's module permissions (e.g., no `finance.view` → Net Profit stat card and Store Health payment-gateway row are omitted, not just blurred).

## Fields
- **Stat cards (6)**: Total Sales, Orders, Visitors, Conversion Rate, Avg. Order Value, Net Profit — each with: label, formatted value, delta % vs. prior period, delta direction (up/down, color-coded), comparison label, 7-point sparkline.
- **Sales Overview**: time-series of `sales` (currency) and `orders` (count) per day, dual Y-axis.
- **Sales by Channel**: per-channel `{channel, pct, amount}`, donut chart + legend + total.
- **Tasks & To-Dos**: `{label, priority: High|Medium|Low}` list, system-generated.
- **Recent Orders**: last N orders — `{order_id, customer_name, total, status, placed_at}`.
- **Inventory Alerts**: `{product_name, stock_status, units_remaining}`.
- **Customer Insights**: New Customers, Returning Customers, Repeat Purchase Rate, Customer Lifetime Value, Churn Risk Customers — each `{value, delta%}`.
- **Marketing Performance**: per-channel `{name, metric_label, metric_value, delta%}`.
- **Store Health**: `{check_name, value, status: Healthy|Warning|Critical}`.
- **Top Products**: rank, product name, units sold, revenue.

## Buttons
- `Customize` — opens widget visibility/order editor.
- `⋮` (more) — export dashboard as PDF/image, reset to default layout, schedule email digest.
- Date range picker — preset ranges (Today, 7d, 30d, 90d, custom).
- `Ask AI Assistant` (top bar, gradient) — opens AI panel/modal from anywhere.
- Per-widget `View all` — deep-links to the owning module (e.g., Recent Orders → `/orders`).
- Sales Overview `Daily ▾` — switch granularity (Hourly/Daily/Weekly/Monthly).
- Sales Overview export icon — downloads chart data as CSV/PNG.
- Quick Actions grid (8 buttons) — Add Product, Create Order, Create Discount, Add Customer, Import Products, Export Data, Send Email, View Reports; each opens the relevant module's create flow in a modal or navigates there.
- AI Business Assistant panel — input field + 4 suggested-prompt chips + `Ask AI Assistant` submit button.

## Tables
- **Recent Orders** table: columns Order (link), Customer, Total, Status (badge), Date. Row click → order detail drawer.

## Filters
- Global date range filter (drives all KPI/chart widgets).
- Sales Overview granularity filter (Daily/Weekly/Monthly).
- Sales by Channel — click a legend row to isolate that channel across Sales Overview (cross-filtering).

## Search
- Global ⌘K search in top bar (not scoped to Dashboard) — searches orders, products, customers, discounts, help docs; not a Dashboard-local search.

## Bulk actions
- None natively on Dashboard (read-mostly page). Tasks & To-Dos items support per-row dismiss/snooze but no multi-select in v1.

## Workflows
1. **Morning triage**: Owner opens Dashboard → scans stat card deltas → reviews Tasks & To-Dos → clicks into any red/orange item → resolves in owning module → returns to Dashboard (badge/task auto-clears via event, see Events).
2. **AI-assisted investigation**: Owner clicks a suggested prompt ("Why did sales increase yesterday?") → AI Assistant streams an answer synthesized from Analytics + Orders data → Owner can pin the answer or drill into the underlying report.
3. **Widget customization**: Owner clicks Customize → drag-reorders/hides widgets → Save → layout persisted to `user_dashboard_preferences`.
4. **Scheduled digest**: Owner enables "Email me this dashboard daily at 8am" from the `⋮` menu → a scheduled job renders the dashboard to PDF/image and emails it.

## Business rules
- Delta % is always computed against the immediately preceding period of equal length (7d range compares to the prior 7d, not the same days last month) unless the merchant explicitly selects "vs. last year."
- Net Profit = Total Sales − COGS − Discounts − Refunds − Payment Processing Fees − Shipping Cost Absorbed; each subtracted line must exist in Finance before Net Profit is shown, otherwise the card shows "Set up cost tracking" CTA instead of a number.
- Inventory Alerts threshold: "Low stock" = on-hand ≤ reorder point (per-product/location setting, default 10); "Out of stock" = on-hand = 0 and not backorderable.
- Churn Risk Customers = customers with ≥1 prior order and no order in the last `churn_window_days` (default 90, configurable) who are not tagged "inactive/opted out."
- Tasks & To-Dos priority: High = revenue-blocking (unfulfilled orders past SLA), Medium = revenue-at-risk (low stock, pending refunds), Low = housekeeping (setup, non-urgent config).

## Validation
- Custom date range: start ≤ end, end ≤ today, max range 366 days (longer ranges route to Analytics' async report builder instead of live widgets).
- Widget customization: at least one widget must remain visible; cannot hide Tasks & To-Dos widget entirely (can collapse, not remove) since it's the primary action surface.

## Notifications
- Real-time badge updates on sidebar Orders count and top-bar messages/notifications icons when new orders/messages arrive while Dashboard is open (via WebSocket/SSE).
- Toast notification on Dashboard when a Store Health check transitions to Warning/Critical (e.g., payment gateway degraded).
- Optional scheduled email/Slack digest (daily/weekly) mirroring the Dashboard's KPI summary.

## Audit logs
- `dashboard.customize` (layout changed) — actor, before/after widget order+visibility.
- `dashboard.export` (PDF/CSV/PNG generated) — actor, format, date range.
- `dashboard.digest_schedule_changed` — actor, schedule, recipients.
- Dashboard itself is read-only for business data, so no data-mutation audit entries originate here; drill-through actions are audited by the owning module.

## Database schema
```
user_dashboard_preferences
  id                uuid PK
  user_id           uuid FK -> users.id
  store_id          uuid FK -> stores.id
  widget_layout     jsonb        -- [{widget_key, position, visible, size}]
  digest_schedule   jsonb null   -- {frequency, time, timezone, recipients[]}
  created_at        timestamptz
  updated_at        timestamptz

analytics_daily_rollup            -- pre-aggregated, powers stat cards + Sales Overview cheaply
  id                uuid PK
  store_id          uuid FK
  date              date
  channel           text null    -- null = all channels
  sales_amount      numeric(14,2)
  orders_count      integer
  visitors_count    integer
  conversion_rate   numeric(6,4)
  avg_order_value   numeric(14,2)
  net_profit        numeric(14,2)
  UNIQUE(store_id, date, channel)
```
Dashboard widgets otherwise read from each domain's tables (`orders`, `products`, `inventory_levels`, `customers`, `marketing_campaigns`) via the Analytics service — see Volume 16 for full ERD.

## APIs
- `GET /api/v1/dashboard/summary?range=7d&channel=all` — returns all stat card + widget payloads in one call (server-composed, cached 60s).
- `GET /api/v1/dashboard/sales-overview?granularity=daily&range=7d`
- `GET /api/v1/dashboard/tasks` / `PATCH /api/v1/dashboard/tasks/{id}` (dismiss/snooze)
- `PUT /api/v1/dashboard/preferences` — save widget layout.
- `POST /api/v1/dashboard/export` — `{format: pdf|png|csv, range}` → async job, returns download URL via webhook/poll.
- `POST /api/v1/ai/assistant/query` — `{prompt, context: "dashboard"}` → streamed response (SSE).

## Events
- `dashboard.viewed` (analytics/telemetry)
- `dashboard.widget_customized`
- `dashboard.task.dismissed` / `dashboard.task.snoozed`
- `dashboard.ai_query.submitted` / `dashboard.ai_query.answered`
- Inbound events that invalidate cached widget data: `order.created`, `order.fulfilled`, `order.refunded`, `inventory.level_changed`, `customer.created`, `payment.settled`.

## Edge cases
- New store, zero orders: all stat cards show "—" with "No data yet for this period" state and a CTA (e.g., "Add your first product") instead of 0%/NaN deltas.
- Prior period has zero as denominator: delta % shows "New" badge instead of dividing by zero.
- Multi-currency store: stat cards show in the merchant's home currency; a tooltip discloses FX rate used and "as of" timestamp.
- Widget data source down (e.g., Analytics service degraded): widget shows cached-as-of timestamp + "Data may be delayed" instead of blocking the whole page.
- Very large numbers (>$1M) — sparkline/format switches to compact notation ($1.2M) with full value on hover.
- Staff user with zero visible widgets (all modules restricted): show a minimal "Welcome" state instead of an empty grid.

## Error handling
- Per-widget error boundaries: one failed widget (e.g., Marketing Performance) shows an inline retry state without breaking the rest of the Dashboard.
- `dashboard/summary` API failure → skeleton loaders persist for 3 retries (exponential backoff) then show full-page error state with "Retry" and a link to status page.
- AI Assistant query failure → inline error in the chat panel with "Try again," original prompt preserved.

## Performance
- `GET /dashboard/summary` served from `analytics_daily_rollup` (pre-aggregated), target p95 < 300ms.
- Widgets stream in independently (skeleton → data) rather than blocking on the slowest widget.
- Sparklines/charts render client-side from a single payload (no per-widget round trip) — see `dashboard-data.ts` mock shape as the contract.
- Dashboard summary cached 60s server-side per store+range+channel; cache busted on high-signal events (new order) for the "Orders"/"Total Sales" cards specifically via targeted invalidation, not full-cache flush.

## Security
- All widget data scoped to `store_id` from the authenticated session — no cross-store data leakage even via direct API calls (enforced at query layer, not just UI).
- Field-level redaction by role (e.g., Net Profit/COGS hidden from non-Finance roles at the API layer, not just CSS).
- AI Assistant prompts/responses logged for abuse monitoring but customer PII is redacted before being sent to the underlying model unless the merchant has explicitly enabled PII-in-AI for their store (compliance toggle).
- Rate limiting on `POST /ai/assistant/query` (per-user, per-store) to prevent cost abuse.

## AI opportunities
- Natural-language querying of any widget ("show me why conversion dropped Tuesday") with drill-down citations back to source data.
- Anomaly detection surfaced proactively (not just Q&A) — e.g., auto-flag a sparkline as anomalous with a one-click "why?" explanation.
- Auto-generated Tasks & To-Dos beyond rule-based thresholds — AI-predicted risks (e.g., "this SKU will stock out in 3 days at current velocity").
- AI-drafted responses to the digest email ("here's what changed and what I'd do about it").
- Forecast overlay on Sales Overview (next 7 days projected, with confidence band).

## UX improvements
- Drag-and-drop widget reordering with live preview (beyond show/hide).
- Per-widget "compare to" toggle (vs. last period / last year / custom).
- Saved dashboard views per role (e.g., a "Finance view" preset).
- Mobile-responsive condensed layout (stat cards as horizontal scroll, widgets stacked) — current implementation is desktop-first; mobile breakpoints are a follow-up.
- Keyboard navigation for widget focus + ⌘K-triggered quick actions.

## Estimated scope (this page)
- ~12 widgets, ~9 API endpoints, 2 primary DB objects (plus reads across ~6 domain tables), ~15 functional requirements, ~10 edge cases documented above.

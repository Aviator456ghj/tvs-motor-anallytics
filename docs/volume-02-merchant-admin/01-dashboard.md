# 2.1 Dashboard

Reference implementation: `/web/src/app/page.tsx` + `/web/src/components/layout/{Topbar,Sidebar}.tsx` + `/web/src/components/dashboard/*` + `/web/src/lib/dashboard-data.ts`.

Designed from scratch using Shopify Admin as the benchmark, then improved where the improvement is concrete and buildable (see **Our Improvements Over Shopify** at the end).

## 1. Purpose
The Dashboard is the merchant's command center. It must answer three questions immediately, without navigating away:
1. **What happened?** — KPIs, sales trend, channel mix, recent orders.
2. **What needs attention?** — Tasks, inventory alerts, store health, notifications.
3. **What should I do next?** — AI Assistant recommendations, Quick Actions.

## 2. Navigation
```
Dashboard
├── Home                    (this page — route "/")
├── Activity Feed           (embedded widget; "View all" → /activity)
├── Notifications           (top-bar bell panel; "View all" → /notifications)
├── Tasks                   (embedded widget; "View all" → /tasks)
├── Analytics Snapshot      (KPI cards + Sales Overview; "View reports" → Volume 2.7 Analytics)
├── Sales Summary           (Sales Overview + Sales by Channel)
├── Recent Orders           (embedded widget; "View all" → Volume 2.2 Orders)
├── Inventory Alerts        (embedded widget; "View all" → Volume 9 Inventory)
├── Customer Insights       (embedded widget; "View all" → Volume 2.4 Customers)
├── Marketing Performance   (embedded widget; "View all" → Volume 2.5 Marketing)
├── Store Health            (embedded widget; "View all" → Settings → System Status)
├── AI Assistant            (top-bar entry point + embedded panel → Volume 13 AI Platform)
└── Quick Actions           (embedded widget)
```
Dashboard is the default landing route after login, first item in the sidebar, no breadcrumb (root page). The global date range control (top-right, e.g. "May 10 – May 16, 2025") scopes every KPI/chart on the page.

## 3. Dashboard Layout

### Top Header
| Element | Behavior |
|---|---|
| Store selector | Switch between the merchant's stores/storefronts (main store, B2B wholesale, outlet) without logging out — see storefront-scoping note in Improvements. |
| Global search (⌘K) | Searches orders, products, customers, discounts, help docs from anywhere. |
| AI assistant | Opens the same conversational assistant that's embedded on this page, from any screen in Admin. |
| App switcher | Grid icon → jumps to Admin, Storefront, Point of Sale, Partner Center, AI Center, Analytics without leaving the tab. |
| Notifications | Bell icon → dropdown panel (see §3.10), unread-count badge. |
| Help | Docs/support shortcut. |
| User profile | Name, role, avatar → account menu (switch account, sign out). |

### Left Sidebar
Dashboard, Orders, Products, Customers, Marketing, Discounts, Content, Markets, Analytics, Finance, Apps, Automations, AI Center, Settings — plus the Sales Channels section (Online Store, Point of Sale, Mobile App, Buy Button, Facebook, Amazon, TikTok Shop, + Add channel). Fully documented per-module in this volume's other pages; unchanged by this redesign.

### Main Dashboard

**3.1 — KPI Cards** (14, in a responsive drag-and-drop grid): Today's Sales, Yesterday's Sales, Monthly Revenue, Orders Today, Pending Orders, Average Order Value, Conversion Rate, Returning Customers, Visitors, Products Sold, Refunds, Profit, Active Carts, Abandoned Checkouts. Each card: label, current-period value, delta vs. the stated comparison point, direction-colored delta (green up / red down), comparison label, 8-point sparkline. Cards default to a sensible order; **Owner/Manager can drag-reorder, resize, or hide any card** (see Improvements — this is the first departure from Shopify's fixed layout).

**3.2 — Sales Graph**: line chart, Sales (left axis, $) + Orders (right axis, count), range selector — **Hourly, Daily, Weekly, Monthly, Yearly, Custom Range** — each granularity backed by its own aggregation, not a client-side re-bucket of daily data (Hourly ≠ Daily ÷ 24). Export (CSV/PNG) and overflow (⋮) menu alongside.

**3.3 — Recent Orders**: full-width table (7 orders' worth of columns needs the room — this is the one widget that does NOT fit a quarter-width card, see Edge Cases). Columns: Order ID, Customer, Total, **Payment** (Paid/Pending/Refunded), **Fulfillment** (Fulfilled/Unfulfilled/Partial), Date, Actions. Payment and Fulfillment are tracked and displayed as two independent statuses (an order can be Paid + Unfulfilled, or Refunded + Fulfilled), not collapsed into one "Status" column. Actions menu per row: **View, Edit, Refund, Print, Archive**.

**3.4 — Inventory Alerts**: four alert categories, each with its own badge color — **Low stock** (warning/amber), **Out of stock** (danger/red), **Overstock** (violet), **Incoming stock** (info/blue, with expected-arrival date). Product icon, name, category badge, status text, unit count.

**3.5 — Customer Insights**: New Customers, Returning Customers, **VIP Customers**, Customer Lifetime Value, Churn Risk — each with value + delta. VIP is a merchant-configurable segment (default: top-decile by lifetime spend, or manually tagged).

**3.6 — Marketing Performance**: Campaign performance rollup — Email (open rate), SMS (click rate), Facebook Ads (ROAS), Google Ads (ROAS), **Ad Spend (MTD)** — pulling from Volume 2.5.

**3.7 — Store Health**: Website Uptime, Checkout status, Payment Gateway, Shipping Providers, **App Errors**, **Security Alerts** — each Healthy (green) / Warning (amber) / Critical (red).

**3.8 — AI Assistant** (embedded panel + top-bar entry point): input box + capability chips exposing exactly what it can do today, not a blank box hoping the merchant guesses:
- Summarize today's business
- Explain revenue changes
- Forecast inventory shortages
- Recommend discounts
- Predict churn
- Suggest marketing actions
- Generate reports
- Answer natural-language questions

**3.9 — Quick Actions**: Add Product, Create Order, Create Discount, Add Customer, Import Products, Export Data, Send Campaign, View Reports — one click into the relevant module's create flow.

**3.10 — Notifications** (top-bar panel, not a separate page in v1): New orders, Failed payments, Refund requests, Chargebacks, Low inventory, Shipping delays, App updates, Staff mentions. Unread indicator per item, "Mark all read," click-through to the source record.

**3.11 — Activity Feed**: chronological, human-readable log of what happened across the store — order placed, payment captured, customer created, product updated, discount activated, inventory adjusted, refund issued, settings changed — each with actor + relative timestamp. Distinct from the Audit Log (Volume 2 global cross-cutting log): Activity Feed is a curated, merchant-facing narrative; Audit Log is the complete, compliance-grade record every event (including ones not shown here) is also written to.

**3.12 — Tasks**: system-generated action items with priority (High/Medium/Low), e.g. "50+ orders to fulfill" (High), "3 low stock products" (Medium), "Complete store setup" (Low).

## 4. User Roles & Permissions
Nine roles, each independently configurable per dashboard component with **view, create, edit, delete, approve, export, manage** granularity — this is finer-grained than Shopify's role model, which is closer to a fixed staff-permission checklist.

| Role | Typical Dashboard scope |
|---|---|
| Owner | Full access to every widget and action, incl. layout customization and role management |
| Administrator | Full access; cannot change billing or remove the Owner |
| Manager | Full operational widgets; Finance widgets (Profit, Refunds $) view-only unless also granted Finance |
| Customer Support | Recent Orders, Customer Insights, Notifications, Activity Feed; no Finance/Marketing spend |
| Inventory Manager | Inventory Alerts (full), Recent Orders (fulfillment columns), Products-adjacent Quick Actions |
| Marketing Manager | Marketing Performance, Customer Insights, AI Assistant marketing capabilities, Quick Actions (Send Campaign, Create Discount) |
| Finance Manager | KPI cards incl. Profit/Refunds, Store Health (Payment Gateway), Finance-adjacent AI capabilities |
| Analyst | Read-only across all widgets, plus Export; no create/edit/approve/manage anywhere |
| Read-only | View every widget the assigned module permissions expose; no buttons enabled |

Underlying permission model: `role_widget_permissions(role_id, widget_key, can_view, can_create, can_edit, can_delete, can_approve, can_export, can_manage)` — a matrix, not a single view/no-view flag, so e.g. Customer Support can `view` Recent Orders but not `export` it, while Analyst can `view` + `export` but never `edit`/`approve`.

- `dashboard.view` — required to load the page at all.
- `dashboard.customize` (= `manage` on the `layout` widget key) — required to reorder/resize/hide widgets, and to save/switch between named layouts (§ Improvements).
- Widget-level visibility is derived from the viewer's per-widget permissions — a widget with no `view` grant is omitted entirely, not shown-and-blurred.

## 5. Workflows
1. **Morning triage**: Owner opens Dashboard → scans KPI deltas → reviews Tasks → clicks a red/orange item → resolves in the owning module → task auto-clears via event.
2. **AI-assisted investigation**: Owner clicks "Explain revenue changes" → AI Assistant streams an answer synthesized from Analytics + Orders → Owner drills into the cited report or pins the answer to Activity Feed.
3. **Layout customization**: Owner drags KPI cards into a new order, hides three they don't use, saves as a named layout ("Ops view") → layout persisted per user+role, switchable from a layout picker (see Improvements — "multiple saved dashboard layouts").
4. **Notification-driven action**: Chargeback notification arrives → merchant clicks it → deep-links straight into the order's dispute view in Finance, notification marked read.
5. **Scheduled AI briefing**: Owner enables a daily 8am summary → AI Platform (Volume 13) generates a natural-language briefing each morning, delivered as an Activity Feed entry + optional email/push.

## 6. Business rules
- Delta % is computed against the immediately preceding period of equal length, unless the merchant selects "vs. last year."
- Profit = Sales − COGS − Discounts − Refunds − Payment Fees − Absorbed Shipping; if any component isn't set up in Finance, the card shows a "Set up cost tracking" CTA instead of a misleading number.
- Inventory Alerts thresholds: Low = on-hand ≤ reorder point (default 10, per-product/location override); Out = 0 and not backorderable; Overstock = on-hand > overstock ceiling (default 3× reorder point) with turnover below a configurable velocity; Incoming = an open purchase order/transfer with an expected date.
- VIP Customers = merchant-defined segment; default rule is top-decile lifetime spend, editable in Customer Insights settings.
- Payment and Fulfillment statuses on Recent Orders are tracked and validated independently — an order cannot show "Fulfilled" fulfillment with no payment captured unless the store's payment terms explicitly allow it (e.g., B2B net terms, Volume 2.13).
- Tasks priority: High = revenue-blocking (SLA-breached unfulfilled orders), Medium = revenue-at-risk (low stock, pending refunds), Low = housekeeping.

## 7. Validation
- Custom date range: start ≤ end ≤ today, max 366 days live (beyond that routes to Analytics' async report builder).
- Layout customization: at least one KPI card and the Tasks widget must remain visible (can collapse, not fully remove) since Tasks is the primary action surface.
- Custom Sales Graph range requires both a start and end date before the chart re-renders (no partial-range flicker).

## 8. Notifications
As catalogued in §3.10, plus: toast on Dashboard when a Store Health check transitions to Warning/Critical while the page is open; optional scheduled email/Slack digest mirroring the KPI summary.

## 9. Audit logs
`dashboard.customize`, `dashboard.layout_saved` / `dashboard.layout_switched`, `dashboard.export`, `dashboard.digest_schedule_changed`, `notification.read` / `notification.marked_all_read`, `task.dismissed` / `task.snoozed`. The Dashboard itself is read-mostly for business data; drill-through mutations (refunding an order via the row Actions menu, for instance) are audited by the owning module (Volume 2.2) in addition to an Activity Feed entry here.

## 10. Database Entities
Named to match the conceptual model this module is designed around; FK targets reference each owning volume's fuller schema.
```
User                  -- Volume 2.10 Settings
Store                 -- Volume 2.10 Settings
DashboardLayout(id, store_id, user_id, name, is_default, role_target, created_at, updated_at)
DashboardWidget(id, layout_id, widget_key, position, size, visible, config jsonb)
Notification(id, store_id, user_id, type, title, body, link, read_at, created_at)
Task(id, store_id, assignee_id null, label, priority[high|medium|low], status, source, created_at, resolved_at)
ActivityLog(id, store_id, actor_type, actor_id, action, entity_type, entity_id, summary, created_at)
KPI(id, store_id, key, date, value, comparison_value, granularity)
SalesSummary(store_id, date, granularity, sales_amount, orders_count)   -- backs the Sales Graph at every range
OrderSummary(store_id, date, orders_today, pending_orders, avg_order_value)
InventoryAlert(id, store_id, product_variant_id, type[low|out|overstock|incoming], count, expected_at null)
CustomerInsight(store_id, date, new_customers, returning_customers, vip_customers, clv, churn_risk_count)
MarketingMetric(id, store_id, channel, metric_key, value, delta, period)
StoreHealth(id, store_id, check_key, value, status[healthy|warning|critical], checked_at)
role_widget_permissions(role_id, widget_key, can_view, can_create, can_edit, can_delete, can_approve, can_export, can_manage)
```
`KPI`/`SalesSummary`/`OrderSummary`/`CustomerInsight` are populated by scheduled rollup jobs per granularity (hourly/daily/weekly/monthly/yearly) rather than computed live — see Performance.

## 11. APIs
`GET /api/v1/dashboard/summary?range=daily`, `GET /api/v1/dashboard/sales-overview?granularity=hourly|daily|weekly|monthly|yearly|custom&from=&to=`, `GET/PATCH /api/v1/dashboard/notifications`, `POST /api/v1/dashboard/notifications/mark-all-read`, `GET/PATCH /api/v1/dashboard/tasks`, `GET/POST/PUT /api/v1/dashboard/layouts` (named layouts), `POST /api/v1/orders/{id}/actions/{view|edit|refund|print|archive}` (Recent Orders row actions, proxied to Volume 2.2), `POST /api/v1/ai/assistant/query` (SSE stream).

## 12. Events
`dashboard.viewed`, `dashboard.layout_saved`, `notification.created` / `notification.read`, `task.created` / `task.resolved`, `ai_query.submitted` / `ai_query.answered`. Inbound events invalidating cached widgets: `order.created/paid/fulfilled/refunded`, `inventory.level_changed`, `customer.created`, `payment.settled`, `app.error_reported`, `security.alert_raised`.

## 13. Edge cases
- New store, zero orders: KPI cards show "—" + "No data yet" CTA instead of 0%/NaN deltas.
- Recent Orders' 7 columns don't fit a quarter-width card at any reasonable breakpoint — it is deliberately laid out full-width with the other three widgets (Inventory Alerts, Customer Insights, AI Assistant) below it, rather than cramming a dense table into a narrow column (this was an actual layout bug caught during implementation — see PR history).
- Store with zero payment-cost data configured: Profit card shows setup CTA, not $0.
- Staff user with zero visible widgets (all permissions restricted): minimal "Welcome" state instead of an empty grid.
- Multi-store merchant switches store mid-session via the Store selector: entire Dashboard payload re-fetches scoped to the new `store_id`; no cross-store data ever renders simultaneously without explicit Cross-Store Dashboard mode (see Improvements).

## 14. Error handling
Per-widget error boundaries — one failed widget doesn't break the page. `dashboard/summary` failure → retried with backoff, then full-page error state. AI Assistant query failure → inline retry, prompt preserved. Notification panel failure → cached last-known list shown with a staleness indicator rather than an empty panel.

## 15. Performance
`dashboard/summary` and the Sales Graph read from pre-aggregated rollups (`SalesSummary`, `KPI`) per granularity — never computed live from raw `orders` rows, so Hourly/Yearly are equally fast. Widgets stream in independently. Recent Orders' full-width table paginates server-side. Layout preferences cached client-side after first load.

## 16. Security
All widget data scoped to `store_id` from session; field-level redaction by role (Profit/Refunds hidden from non-Finance roles at the API layer); AI Assistant prompts/responses logged for abuse monitoring with PII redaction by default; rate limiting on the AI query endpoint; Store selector switch re-validates the user's membership in the target store server-side before returning any data.

## 17. AI opportunities
The 8 capabilities in §3.8 are the v1 surface. Beyond that: proactive anomaly detection (flag an anomalous sparkline before being asked); AI-authored Tasks beyond rule-based thresholds ("this SKU stocks out in 3 days at current velocity"); forecast overlay on the Sales Graph; AI-drafted daily briefing delivered into Activity Feed; natural-language widget queries with drill-down citations.

## 18. Our Improvements Over Shopify
Shopify's Admin home is informative but fixed: one layout, no saved views, no cross-store rollup, and "AI" limited to Shopify Magic's narrow content-generation tools. This module improves on each of those specifically:

1. **Fully customizable drag-and-drop widgets** — every KPI card and panel can be reordered, resized, or hidden per user (`DashboardWidget.position/size/visible`), not just toggled on a fixed grid.
2. **Multiple saved dashboard layouts** (CEO, Operations, Marketing, Finance) — `DashboardLayout` is a first-class entity a user can create, name, and switch between, each with its own widget set.
3. **AI-generated daily briefings** — a proactive morning summary in Activity Feed, not just a reactive Q&A box.
4. **Cross-store dashboards** — the Store selector (§3 Top Header) is the seed of a future rollup view across a merchant's stores (main + wholesale + outlet), which Shopify requires separate admin sessions for.
5. **Real-time collaboration** — Activity Feed + Staff mentions in Notifications lay the groundwork for live presence/comments on records (future volume).
6. **Role-specific dashboards** — the nine-role, per-widget permission matrix (§4) is materially finer-grained than Shopify's staff permission checklist.
7. **Predictive alerts** — Tasks and Inventory Alerts are designed to accept AI-generated entries (stockout forecasts, churn risk) alongside rule-based ones, not exclusively threshold-based.
8. **Voice interaction** — the AI Assistant input is spec'd to accept voice input as an alternate modality (implementation tracked in Volume 13).
9. **Command palette for instant actions** — ⌘K search is scoped to expand into an action palette (not just navigation) so "create discount 20% off" can be typed directly, not only clicked via Quick Actions.
10. **Embedded workflow automation** — Quick Actions and Tasks are designed to trigger Automation Engine (Volume 14) rules directly from the Dashboard, e.g. "resolve this task by running the low-stock reorder automation," rather than only linking out to another module.

## 19. UX improvements
Drag-and-drop layout editing with live preview; per-widget "compare to" toggle (last period / last year / custom); mobile-responsive condensed layout (current implementation is desktop-first — tracked as a follow-up); keyboard navigation for widget focus.

## 20. Estimated scope (this page)
14 KPI cards, 12 dashboard sections/widgets, ~15 API endpoints, 13 named DB entities (plus the cross-cutting permission matrix), 9 roles × 7 permission actions, ~10 documented edge cases.

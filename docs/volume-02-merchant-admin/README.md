# Volume 2 — Merchant Admin

Status: ✅ Full depth. The Merchant Admin is the operator-facing control panel — every page a store Owner, Manager, or scoped staff member uses to run the business. This volume documents all 13 modules to the full CommerceOS page-spec template. The **Dashboard** module has a working reference implementation in `/web`.

## Global shell (applies to every page in this volume)

**Layout**: Fixed left sidebar (248px expanded / 76px collapsed) + top bar + main content + footer. See `/web/src/components/layout/{Sidebar,Topbar,Footer,AppShell}.tsx`.

**Sidebar** — primary nav (Dashboard, Orders, Products, Customers, Marketing, Discounts, Content, Markets, Analytics, Finance, Apps, Automations, AI Center) + Sales Channels section (Online Store, Point of Sale, Mobile App, Buy Button, Facebook, Amazon, TikTok Shop, + Add channel) + Settings + Collapse toggle.

**Top bar** — global search (⌘K), "Ask AI Assistant" entry point, share, messages (unread badge), notifications (unread badge), help, account menu (avatar, name, role, sign-out/switch-store).

**Roles referenced throughout this volume** (see Volume 1 §1.5 for full persona detail):
| Role | Scope |
|---|---|
| Owner | Full access to every module, billing, and role management |
| Manager | Full operational access; no billing/store-deletion/role-management |
| Staff (custom) | Per-module read/write/none, assigned by Owner/Manager |
| Marketing | Marketing, Discounts, Content, Analytics (read) |
| Finance | Finance, Analytics (read), Orders (read) |
| Support | Orders, Customers; no Products/Finance write |
| App (API/OAuth) | Scoped per granted permission, non-interactive |

**Cross-cutting audit logging**: every create/update/delete/status-change in this volume writes an `audit_log` row (see each page's Audit Logs section) with `actor_id, actor_type, action, entity_type, entity_id, before, after, ip, user_agent, created_at`. Retained 2 years minimum (configurable, compliance-driven).

## Modules in this volume

1. [Dashboard](./01-dashboard.md) — store-health command center, KPIs, AI assistant entry point
2. [Orders](./02-orders/README.md) — order lifecycle, fulfillment, payments, refunds. 9-screen module; [2.2.1 Orders Dashboard](./02-orders/01-orders-dashboard.md) is built
3. [Products](./03-products.md) — catalog, variants, media, inventory linkage
4. [Customers](./04-customers.md) — customer records, segments, CRM-lite
5. [Marketing](./05-marketing.md) — campaigns, email/SMS, ads integration
6. [Discounts](./06-discounts.md) — promo codes, automatic discounts, bundles
7. [Analytics](./07-analytics.md) — reports, custom dashboards, exports
8. [Finance](./08-finance.md) — payouts, ledger, taxes, reconciliation
9. [Apps](./09-apps.md) — app marketplace, installed apps, permissions
10. [Settings](./10-settings.md) — store config, users/roles, domains, checkout
11. [Markets](./11-markets.md) — multi-region, currency, localization
12. [Content](./12-content.md) — CMS pages, blog, navigation menus
13. [B2B](./13-b2b.md) — wholesale price lists, company accounts, net terms

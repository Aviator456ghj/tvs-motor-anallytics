# Architecture

## Today: modular monolith, tomorrow: microservices

The product spec's "scalable microservices" list (Auth, User, Business,
Category, Booking, Payment, Notification, Review, Chat, Search,
Recommendation, AI, Analytics, Admin, Media Service) maps directly onto this
codebase — but as **routers inside one FastAPI app**, not separate deployed
services:

```
backend/app/routers/
  auth.py          → Authentication Service
  businesses.py     → Business Service
  categories.py      → Category Service
  services.py         → Catalog (Service/Package/Portfolio) Service
  availability.py      → Availability/Calendar Service
  bookings.py            → Booking Service
  payments.py              → Payment Service
  reviews.py                 → Review Service
  notifications.py            → Notification Service
  chat.py                       → Chat Service
  coupons.py                     → Promotions Service
  customers.py                    → Wishlist / Support Service
  admin.py                          → Admin Service
  analytics.py                       → Analytics Service
  search.py                            → Search Service
  ai.py                                  → AI/Recommendation Service
```

Each router only talks to its own tables plus a narrow set of shared ones
(mainly `Notification`, created as a side effect of booking/payment state
changes). That boundary is deliberate: splitting any router out into its own
deployed FastAPI service later is a matter of standing up a new process and
pointing it at the same Postgres (or its own database, once you're ready to
split data too) — not a rewrite. Start with the modular monolith; split when
a specific module's load profile actually demands independent scaling
(Search and AI are the most likely first candidates).

## Data model

22 tables, defined in `backend/app/models/`. The core entity relationships:

```
User ──1:1── BusinessProfile ──1:N── Service ──1:N── Package
                    │                                    │
                    ├─1:N── Employee                     │
                    ├─1:N── BusinessDocument (KYC)        │
                    ├─1:N── PortfolioItem                 │
                    ├─1:N── AvailabilitySlot              │
                    └─N:M── Category (via BusinessCategory)
                                                           │
User (customer) ──1:N── Booking ───────────────────────────┘
                            │
                            ├─1:N── Payment
                            └─1:1── Review

Category (self-referential: parent_id) — main category → subcategories
```

`Category.parent_id` is the only structural piece that makes this a
*horizontal* marketplace instead of a single-vertical app: every main
category (Photography, Home Services, Legal, …) and its subcategories live
in the same table, and `Service`/`BusinessCategory` reference whichever
subcategory applies. Nothing else in the schema is category-specific.

## Booking state machine

```
requested → accepted → scheduled → in_progress → completed
    ↓           ↓
rejected    cancelled (also reachable from scheduled/in_progress)
```

Enforced server-side in `bookings.py::_NEXT_STATUS` — invalid transitions
(e.g. `requested → completed`) return 400. Commission is calculated at
booking-creation time (`business.commission_rate × amount_total`) and stored
on the booking row, so changing a business's commission rate later doesn't
retroactively affect past bookings.

## Shopify-parity features

A booking is the marketplace's "order" — the Business Portal's Orders,
Payouts, Customers, and Staff Accounts sections mirror the parts of Shopify
Admin that translate to a services business (not the e-commerce-specific
parts like inventory, shipping, or themes, which don't apply here):

- **Orders** (`bookings.py`): search/filter/tag/CSV-export on top of the
  existing booking list, plus `BookingEvent` — an append-only timeline
  logging every status change automatically and every manual note/tag
  edit. Timeline visibility is role-scoped: `note` and `tag` events are
  internal-only and stripped from customer-facing responses
  (`_INTERNAL_ONLY_EVENT_TYPES`); the customer still sees status changes,
  payments, and refunds on their own order.
- **Refunds** (`bookings.py::refund_booking`): partial or full, credited to
  the customer's `wallet_balance`, capped at `amount_paid - amount_refunded`.
- **Payouts** (`payouts.py`): `available_balance = gross_paid - refunded -
  commission_on_completed_bookings - already_paid_out`. Requesting a payout
  is simulated as instant (see docs/ROADMAP.md) but the ledger math is real.
- **Customer 360** (`businesses.py::list_business_customers` /
  `get_business_customer`): per-business customer list with lifetime spend
  and order history, computed with a `GROUP BY customer_id` over bookings —
  no separate CRM table needed.
- **Staff accounts** (`core/business_access.py`, `models/business.py::BusinessStaff`):
  a business is reachable by its owner (implicit, full access) or by any
  `BusinessStaff` row granting a tier (`staff` < `manager` < `owner`).
  `require_business_access(min_role)` is the single dependency every
  business router uses instead of an ad-hoc `owner_id` check, so a
  permission tier applies uniformly everywhere: catalog/bookings/availability
  need `staff`+, earnings/analytics/customers/reviews need `manager`+,
  company-profile/KYC/payouts/staff-management need `owner`. This is
  enforced server-side (tested: a `staff`-tier user gets a 403 on
  owner-only endpoints even if they know the URL) — not just hidden nav
  items in the frontend.

The Business Portal's shell (`components/BusinessShell.tsx`) also went
through a real Shopify-admin-depth pass, on the theory that "same UI/UX
performance as Shopify" means the *interaction model*, not the color
palette:

- **Icon sidebar with collapsible sections** (`components/icons.tsx`) — a
  flat top-level nav (Home, Orders, Products, Customers, Discounts, Finance,
  Analytics, Online Store, Settings) where the active section expands its
  sub-pages inline, mirroring Shopify Admin's actual navigation pattern
  rather than a flat always-expanded tree.
- **A real top bar**: global search, a notification bell with unread count
  and mark-as-read, and a "Create" quick-action menu (Create order / Add
  service / Add discount) reachable from any business page — Shopify's
  global "+" pattern.
- **A Settings hub** (`/business/settings`) instead of stuffing every
  settings page into the sidebar — cards grouped by Business / Payments /
  Team / Compliance, linking out to Locations, Payout Account, Policies,
  Notifications, Staff, Team Roster, KYC, and Plan & Billing.
- **Further Shopify-parity additions**: business-scoped discount codes
  (`Coupon.business_id`, previously platform-only), manual/phone order
  creation (`POST /bookings/manual` — Shopify's Draft Order equivalent,
  requires the customer to already have an account), a payout bank account
  gate (`BusinessPayoutAccount` — payout requests 400 without one, matching
  Shopify's requirement to add a payout method before Shopify Payments
  pays out), a unified transactions ledger with a running balance
  (`GET /payouts/me/transactions`), and a small reports library (top
  services by revenue, repeat-customer rate, booking funnel).
- **A shared toast system** (`components/Toast.tsx`) replaces page-local
  inline error/success `<p>` tags for anything built or touched in this
  pass, matching Shopify's snackbar-confirmation pattern.

## What's fully implemented vs. intentionally stubbed

| Area | Status | Notes |
|---|---|---|
| Auth, RBAC, booking lifecycle, commission math, coupon discounts | **Real** | Exercised end-to-end in the smoke test; see `docs/ROADMAP.md` for nothing — this is done. |
| Admin approval / KYC workflow | **Real** | Business goes live only after `is_approved=True`; KYC documents drive `kyc_status`. |
| Payments (Razorpay/Stripe) | **Stubbed** | `payments.py::_charge_via_gateway` returns a mock reference synchronously. Swap for real order-creation + webhook capture — see ROADMAP. |
| File storage (portfolio, KYC docs) | **Stubbed** | Endpoints accept a `file_url` string; no upload/presign flow yet. Swap for S3-compatible presigned uploads. |
| AI (recommendations, pricing, chatbot, fraud, demand forecast) | **Stubbed with real contracts** | `ai.py` implements deterministic placeholder logic (e.g. rating-based ranking) behind the exact endpoint shape a real model would use — see ROADMAP for the swap-in plan per endpoint. |
| Search | **Stubbed** | Postgres `ILIKE` in `search.py` and `businesses.py::search_businesses`. Swap for Elasticsearch/OpenSearch once catalog size warrants it — response shape is designed to stay stable. |
| Chat | **Partial** | REST polling (`chat.py`) works today; no WebSocket push yet. Thread/message persistence is already the right shape for a `/ws/chat/{thread_id}` upgrade. |
| Subscriptions / Invoices | **Read-only views** | `Subscription`/`Invoice` models exist; the frontend derives invoice-like summaries from completed bookings rather than a dedicated billing engine, since there's no payment-gateway subscription flow yet. |

## Frontend structure

```
frontend/app/
  page.tsx, browse/, search/, provider/[slug]/   → public marketing + discovery
  login/, register/                               → auth
  dashboard/**                                      → Customer Portal (role: customer)
  business/**                                         → Business Portal (role: business)
  admin/**                                              → Super Admin Panel (role: admin)
```

Each portal has its own `layout.tsx` that gates on role (`useRequireRole`)
and renders a shared `<DashboardShell>` with a per-portal sidebar config —
adding a new sidebar section is a one-line addition to the `sections` array
plus a new `page.tsx`, not a new layout.

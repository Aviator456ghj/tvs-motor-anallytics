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

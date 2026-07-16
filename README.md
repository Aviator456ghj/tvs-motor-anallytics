# ServicesOS — The Operating System for Local & Online Services

A horizontal services marketplace: one Customer Portal, one Business Portal, one
Super Admin Panel, and one shared booking/payment/review/notification engine
that every vertical (photography, home services, events, tutoring, legal,
beauty, and 90+ more) plugs into. Think Amazon + Urban Company + Justdial +
Fiverr + Booking.com, built as a single modular platform instead of a
category-specific app.

This repo is a working, runnable MVP of that platform: a FastAPI backend with
the full domain model wired up end-to-end (auth → categories → business
listings → bookings → payments → reviews → notifications → admin approval →
commission/analytics), a Next.js frontend implementing every sidebar section
from the product spec across all three portals, and seed data covering the
complete 100+ category taxonomy.

## Quick start

### Option A — Docker (recommended)

```bash
cp backend/.env.example backend/.env   # edit if needed
docker compose up --build
docker compose run --rm seed           # one-time: seed categories + demo data
```

- API: http://localhost:8000/docs (interactive OpenAPI docs)
- Web: http://localhost:3000

### Option B — Run locally

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point DATABASE_URL at Postgres, or use SQLite for a quick spin:
export DATABASE_URL="sqlite:///./dev.db"
python -m app.seed.seed          # seeds 113 categories + 4 demo businesses
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
export NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev
```

### Demo logins (all seeded, password `Password@123`)

| Role     | Email                              |
|----------|-------------------------------------|
| Admin    | admin@servicesos.io                 |
| Customer | customer@servicesos.io              |
| Business | abc.photography@servicesos.io       |
| Business | framecraft.films@servicesos.io      |
| Business | pixelpost.studio@servicesos.io      |
| Business | celebrate.events@servicesos.io      |

## What's actually implemented

This isn't a mockup — the full booking lifecycle runs end-to-end against a
real database: register → browse categories → view a provider → book a
package → pay an advance → business accepts/schedules/completes → pay the
balance → leave a review → admin sees revenue and commission. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for what's fully wired vs.
intentionally stubbed (payment gateways, file storage, real AI models,
Elasticsearch, WebSockets), and [docs/ROADMAP.md](docs/ROADMAP.md) for how to
extend each stub without touching the core engine.

- **Backend** (`backend/`): FastAPI + SQLAlchemy + Postgres, JWT auth with
  three roles (customer/business/admin), 22 tables covering the entire
  domain, ~90 REST endpoints. Booking commission, advance/remaining payment
  split, coupon discounts, KYC approval workflow, and admin dashboard metrics
  are all real business logic, not placeholders.
- **Frontend** (`frontend/`): Next.js 14 App Router + TypeScript + Tailwind.
  Every sidebar section from the product spec (Customer, Business, Super
  Admin) is a routed page wired to the real API — not a static wireframe.
- **Seed data** (`backend/app/seed/`): the full 16-main-category / 97-sub-category
  taxonomy from the spec, plus 4 demo businesses in the recommended launch
  verticals (Photography → Videography → Editing → Events) across 3 cities.

## Repo layout

```
backend/          FastAPI app (see backend/app/routers for the API surface)
frontend/          Next.js app (see frontend/app for every portal page)
docs/
  ARCHITECTURE.md  System design, module boundaries, what's stubbed
  ROADMAP.md       How to build out AI, payments, search, realtime chat
  CATEGORIES.md    The full category taxonomy as seeded
docker-compose.yml Postgres + Redis + API + Web, one command to run it all
```

## Why start with Photography → Videography → Editing → Events

Per the product recommendation: don't launch every vertical at once. The
booking/payment/review/notification engine is category-agnostic by design —
`Category`, `Service`, and `Package` are the only vertical-specific tables,
and everything downstream (booking state machine, commission calculation,
payments, reviews) is shared. Adding a new vertical is a seed-data change
(`backend/app/seed/categories_data.py`), not a code change — confirmed by
the demo data already spanning 4 verticals with zero conditional logic in
the booking flow.

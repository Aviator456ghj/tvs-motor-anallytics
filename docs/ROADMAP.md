# Roadmap

Ordered roughly by what unblocks a real pilot launch first.

## 1. Payments — real gateway integration

`backend/app/routers/payments.py::_charge_via_gateway` is a stub that
returns a mock transaction reference synchronously. To go live:

- Razorpay: create an Order server-side, return the order id to the
  frontend, collect payment via Razorpay Checkout, verify the webhook
  signature, then mark the `Payment` row `success` from the webhook handler
  (not from the client callback — never trust the client for payment state).
- Stripe: same shape with PaymentIntents + webhook `payment_intent.succeeded`.
- Add a `POST /payments/webhook/{gateway}` endpoint per gateway; keep the
  `Payment` model and `payment_type` (advance/remaining/full/refund) as-is —
  the booking flow doesn't need to change, only how `status` transitions to
  `success`.

## 2. File storage — portfolio & KYC uploads

Endpoints currently accept a `file_url` string (`portfolio.py`,
`businesses.py::upload_document`). Add:

- An S3-compatible bucket (AWS S3, Cloudflare R2, or MinIO for self-hosted).
- A presigned-upload endpoint (`POST /uploads/presign`) returning a PUT URL;
  the frontend uploads directly to storage, then calls the existing
  `POST /portfolio` / `POST /businesses/me/documents` with the resulting
  public URL. No change needed to the existing endpoints' request shape.

## 3. AI Service — swap placeholders for real models

Every endpoint in `ai.py` documents its intended replacement in a docstring.
Priority order for a real pilot:

1. **Fake-review detection** (`reviews.py::_looks_fake`) — currently a
   keyword heuristic. Swap for a lightweight spam/sentiment classifier;
   the `Review.is_flagged` / `flagged_reason` columns already exist.
2. **Recommendations** (`ai.py::recommend_providers`) — currently
   rating-sorted. Swap for collaborative filtering once there's enough
   booking history to train on.
3. **Chatbot** (`ai.py::chatbot_reply`) — currently rule-based. Swap for an
   LLM with retrieval over categories/FAQ/booking-status tools (a good fit
   for Claude with tool use against the existing `/bookings`, `/categories`
   endpoints).
4. **Pricing suggestions / demand forecasting** — need more booking volume
   before a real model outperforms the current median/trailing-count
   baselines; not urgent pre-launch.

## 4. Search — Elasticsearch/OpenSearch

`search.py` and `businesses.py::search_businesses` use Postgres `ILIKE`,
fine through a few thousand businesses. When it isn't:

- Index `BusinessProfile` + `Service` + `Category` documents on
  create/update (a Celery task triggered from the relevant router is the
  natural hook — Celery is already a dependency).
- Keep `GET /search` and `GET /businesses/search`'s response shape
  identical; swap the query implementation only.

## 5. Realtime — WebSocket chat & notifications

`chat.py` is REST polling today. `ChatThread`/`ChatMessage` are already the
right shape for a push upgrade:

- Add `WS /ws/chat/{thread_id}` authenticated via the same JWT, broadcasting
  new `ChatMessage` rows to connected clients (Redis pub/sub for
  multi-instance fan-out — Redis is already a dependency).
- Same pattern for live notification delivery instead of the current
  poll-on-page-load.

## 6. New verticals beyond the launch set

Adding a vertical is a data change, not a code change:

1. Add the main category + subcategories to
   `backend/app/seed/categories_data.py::CATEGORY_TAXONOMY`.
2. Re-run `python -m app.seed.seed` (idempotent — safe to re-run against an
   existing database).
3. Businesses in that category can immediately create services/packages
   through the existing Business Portal — no new UI or backend code needed.

## 7. Production hardening (before real users/money)

- Swap `Base.metadata.create_all()` (dev convenience in `main.py`) for
  Alembic migrations — the `backend/alembic/` scaffold is in place; run
  `alembic revision --autogenerate` against the current models to generate
  the first migration.
- Rotate `JWT_SECRET` out of `.env.example` defaults; use a secrets manager.
- Add rate limiting on `/auth/*` and `/bookings` (a Redis-backed limiter is
  a natural fit given Redis is already provisioned).
- Structured logging + error tracking (Sentry or equivalent) — none wired
  up yet.
- CI: run `pytest` (backend) and `next build` (frontend) on every PR; neither
  is wired to a CI config in this repo yet.

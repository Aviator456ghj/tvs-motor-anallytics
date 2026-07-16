"""
AI Service stubs.

These endpoints define the contract the frontend and other services call
today, with deterministic placeholder logic. Each is documented with the
real model/approach intended to replace it — swap the function body only,
the route + response shape are meant to stay stable. See docs/ROADMAP.md.
"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.booking import Booking
from app.models.business import BusinessProfile
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/recommendations")
def recommend_providers(category_slug: str | None = None, limit: int = 6, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Placeholder: ranks by rating * log(bookings). Real version: collaborative
    filtering / learned-to-rank model using booking history, location, and
    category affinity embeddings."""
    query = db.query(BusinessProfile).filter(BusinessProfile.is_approved.is_(True))
    if user.city:
        query = query.filter(BusinessProfile.city == user.city)
    top = query.order_by(BusinessProfile.rating_avg.desc(), BusinessProfile.rating_count.desc()).limit(limit).all()
    return [{"business_id": b.id, "company_name": b.company_name, "slug": b.slug, "score": b.rating_avg} for b in top]


@router.post("/pricing-suggestion")
def suggest_pricing(category_id: uuid.UUID, city: str | None = None, db: Session = Depends(get_db)):
    """Placeholder: returns the market median/quartiles for packages in this
    category+city from existing data. Real version: regression model factoring
    in seasonality, provider experience, and demand forecasts."""
    from app.models.catalog import Package, Service

    query = db.query(Package.price).join(Service, Service.id == Package.service_id).filter(Service.category_id == category_id)
    if city:
        query = query.join(BusinessProfile, BusinessProfile.id == Service.business_id).filter(BusinessProfile.city == city)
    prices = sorted(float(p[0]) for p in query.all())
    if not prices:
        return {"suggested_min": None, "suggested_median": None, "suggested_max": None, "sample_size": 0}
    n = len(prices)
    return {
        "suggested_min": prices[0],
        "suggested_median": prices[n // 2],
        "suggested_max": prices[-1],
        "sample_size": n,
    }


@router.get("/demand-forecast")
def demand_forecast(business_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    """Placeholder: trailing-30-day booking count as a naive forecast. Real
    version: time-series model (e.g. Prophet/ARIMA) per category+city."""
    since = datetime.utcnow() - timedelta(days=30)
    query = db.query(func.count(Booking.id)).filter(Booking.created_at >= since)
    if business_id:
        query = query.filter(Booking.business_id == business_id)
    count = query.scalar()
    return {"trailing_30_day_bookings": count, "forecast_next_30_days": count}


@router.post("/chatbot")
def chatbot_reply(message: str, user: User = Depends(get_current_user)):
    """Placeholder rule-based responder. Real version: LLM-backed assistant
    with retrieval over categories/FAQ/booking-status tools."""
    lowered = message.lower()
    if "refund" in lowered:
        reply = "Refunds are processed within 5-7 business days after a cancelled booking. Want me to check a specific booking?"
    elif "book" in lowered:
        reply = "I can help you find a provider — which service category are you looking for?"
    else:
        reply = "Thanks for reaching out! A support agent will follow up, or you can browse categories to get started."
    return {"reply": reply}


@router.get("/fraud-signals/business/{business_id}")
def fraud_signals(business_id: uuid.UUID, db: Session = Depends(get_db)):
    """Placeholder heuristic signals for admin review. Real version: anomaly
    detection over booking velocity, payment failure rate, and device/IP
    fingerprinting."""
    cancelled = db.query(func.count(Booking.id)).filter(Booking.business_id == business_id, Booking.status == "cancelled").scalar()
    total = db.query(func.count(Booking.id)).filter(Booking.business_id == business_id).scalar()
    cancellation_rate = round(cancelled / total, 2) if total else 0
    risk = "high" if cancellation_rate > 0.4 else "medium" if cancellation_rate > 0.2 else "low"
    return {"business_id": business_id, "cancellation_rate": cancellation_rate, "risk_level": risk}

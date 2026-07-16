from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_business
from app.models.booking import Booking
from app.models.business import BusinessProfile
from app.models.engagement import Review
from app.models.enums import BookingStatus
from app.models.payment import Payment
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/business/me")
def my_business_analytics(days: int = 30, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
    if not business:
        raise HTTPException(404, "Business profile not found")

    since = datetime.utcnow() - timedelta(days=days)
    bookings_q = db.query(Booking).filter(Booking.business_id == business.id)

    total_bookings = bookings_q.count()
    bookings_period = bookings_q.filter(Booking.created_at >= since).count()
    completed = bookings_q.filter(Booking.status == BookingStatus.completed).count()
    cancelled = bookings_q.filter(Booking.status == BookingStatus.cancelled).count()

    gross_earnings = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .join(Booking, Booking.id == Payment.booking_id)
        .filter(Booking.business_id == business.id)
        .scalar()
    )
    commission_paid = (
        db.query(func.coalesce(func.sum(Booking.commission_amount), 0))
        .filter(Booking.business_id == business.id, Booking.status == BookingStatus.completed)
        .scalar()
    )
    net_earnings = float(gross_earnings) - float(commission_paid)

    status_breakdown = dict(
        db.query(Booking.status, func.count(Booking.id)).filter(Booking.business_id == business.id).group_by(Booking.status).all()
    )

    return {
        "total_bookings": total_bookings,
        "bookings_last_n_days": bookings_period,
        "completed_bookings": completed,
        "cancelled_bookings": cancelled,
        "conversion_rate": round(completed / total_bookings, 2) if total_bookings else 0,
        "gross_earnings": float(gross_earnings),
        "commission_paid": float(commission_paid),
        "net_earnings": net_earnings,
        "rating_avg": business.rating_avg,
        "rating_count": business.rating_count,
        "status_breakdown": {k.value: v for k, v in status_breakdown.items()},
    }


@router.get("/business/me/reviews-summary")
def my_reviews_summary(user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
    if not business:
        raise HTTPException(404, "Business profile not found")
    breakdown = dict(
        db.query(Review.rating, func.count(Review.id)).filter(Review.business_id == business.id).group_by(Review.rating).all()
    )
    return {"rating_avg": business.rating_avg, "rating_count": business.rating_count, "breakdown": {str(k): v for k, v in breakdown.items()}}

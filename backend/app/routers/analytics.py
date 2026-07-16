from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.business_access import require_business_access
from app.core.database import get_db
from app.models.booking import Booking
from app.models.business import BusinessProfile
from app.models.catalog import Package, Service
from app.models.engagement import Review
from app.models.enums import BusinessStaffRole, BookingStatus
from app.models.payment import Payment

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/business/me")
def my_business_analytics(
    days: int = 30,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
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


@router.get("/business/me/timeseries")
def my_business_timeseries(
    days: int = 30,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    since = (datetime.utcnow() - timedelta(days=days - 1)).date()
    rows = (
        db.query(func.date(Booking.created_at).label("d"), func.count(Booking.id), func.coalesce(func.sum(Booking.amount_paid), 0))
        .filter(Booking.business_id == business.id, Booking.created_at >= since)
        .group_by("d")
        .order_by("d")
        .all()
    )
    by_day = {str(r[0]): {"bookings": r[1], "revenue": float(r[2])} for r in rows}
    series = []
    for i in range(days):
        d = since + timedelta(days=i)
        key = str(d)
        entry = by_day.get(key, {"bookings": 0, "revenue": 0.0})
        series.append({"date": key, **entry})
    return series


@router.get("/business/me/reviews-summary")
def my_reviews_summary(
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    breakdown = dict(
        db.query(Review.rating, func.count(Review.id)).filter(Review.business_id == business.id).group_by(Review.rating).all()
    )
    return {"rating_avg": business.rating_avg, "rating_count": business.rating_count, "breakdown": {str(k): v for k, v in breakdown.items()}}


@router.get("/business/me/reports/top-services")
def top_services_report(
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Service.title, func.count(Booking.id), func.coalesce(func.sum(Booking.amount_paid), 0))
        .join(Booking, Booking.service_id == Service.id)
        .filter(Service.business_id == business.id)
        .group_by(Service.title)
        .order_by(func.coalesce(func.sum(Booking.amount_paid), 0).desc())
        .all()
    )
    return [{"service": title, "bookings": count, "revenue": float(revenue)} for title, count, revenue in rows]


@router.get("/business/me/reports/repeat-customers")
def repeat_customers_report(
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Booking.customer_id, func.count(Booking.id))
        .filter(Booking.business_id == business.id)
        .group_by(Booking.customer_id)
        .all()
    )
    total_customers = len(rows)
    repeat_customers = sum(1 for _cid, count in rows if count > 1)
    return {
        "total_customers": total_customers,
        "repeat_customers": repeat_customers,
        "repeat_rate": round(repeat_customers / total_customers, 2) if total_customers else 0,
    }


@router.get("/business/me/reports/funnel")
def booking_funnel_report(
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(Booking.id)).filter(Booking.business_id == business.id).scalar()
    accepted_or_later = (
        db.query(func.count(Booking.id))
        .filter(Booking.business_id == business.id, Booking.status != BookingStatus.requested, Booking.status != BookingStatus.rejected)
        .scalar()
    )
    scheduled_or_later = (
        db.query(func.count(Booking.id))
        .filter(Booking.business_id == business.id, Booking.status.in_(["scheduled", "in_progress", "completed"]))
        .scalar()
    )
    completed = db.query(func.count(Booking.id)).filter(Booking.business_id == business.id, Booking.status == BookingStatus.completed).scalar()
    return [
        {"stage": "Requested", "count": total},
        {"stage": "Accepted", "count": accepted_or_later},
        {"stage": "Scheduled", "count": scheduled_or_later},
        {"stage": "Completed", "count": completed},
    ]

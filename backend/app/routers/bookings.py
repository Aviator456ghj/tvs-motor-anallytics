import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_business, require_customer
from app.models.booking import Booking
from app.models.business import BusinessProfile
from app.models.catalog import Package, Service
from app.models.engagement import Coupon, Notification
from app.models.enums import BookingStatus, DiscountType, NotificationType, UserRole
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingOut, BookingStatusUpdate

router = APIRouter(prefix="/bookings", tags=["bookings"])

_NEXT_STATUS = {
    BookingStatus.requested: {BookingStatus.accepted, BookingStatus.rejected, BookingStatus.cancelled},
    BookingStatus.accepted: {BookingStatus.scheduled, BookingStatus.cancelled},
    BookingStatus.scheduled: {BookingStatus.in_progress, BookingStatus.cancelled},
    BookingStatus.in_progress: {BookingStatus.completed, BookingStatus.cancelled},
}


def _notify(db: Session, user_id: uuid.UUID, ntype: NotificationType, title: str, message: str):
    db.add(Notification(user_id=user_id, type=ntype, title=title, message=message))


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    business = db.get(BusinessProfile, payload.business_id)
    if not business or not business.is_approved:
        raise HTTPException(404, "Business not found")
    service = db.query(Service).filter(Service.id == payload.service_id, Service.business_id == business.id).first()
    if not service:
        raise HTTPException(404, "Service not found")
    package = db.query(Package).filter(Package.id == payload.package_id, Package.service_id == service.id).first()
    if not package:
        raise HTTPException(404, "Package not found")

    amount_total = float(package.price)
    discount_amount = 0.0
    if payload.coupon_code:
        coupon = db.query(Coupon).filter(Coupon.code == payload.coupon_code, Coupon.is_active.is_(True)).first()
        if not coupon:
            raise HTTPException(400, "Invalid coupon code")
        if coupon.valid_to and coupon.valid_to < datetime.utcnow():
            raise HTTPException(400, "Coupon expired")
        if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
            raise HTTPException(400, "Coupon usage limit reached")
        if amount_total < float(coupon.min_order_value):
            raise HTTPException(400, f"Minimum order value for this coupon is {coupon.min_order_value}")
        if coupon.discount_type == DiscountType.flat:
            discount_amount = float(coupon.discount_value)
        else:
            discount_amount = amount_total * float(coupon.discount_value) / 100
            if coupon.max_discount:
                discount_amount = min(discount_amount, float(coupon.max_discount))
        coupon.usage_count += 1
        amount_total = max(amount_total - discount_amount, 0)

    commission_rate = float(business.commission_rate)
    commission_amount = round(amount_total * commission_rate, 2)

    booking = Booking(
        customer_id=user.id,
        business_id=business.id,
        service_id=service.id,
        package_id=package.id,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        service_address=payload.service_address,
        notes=payload.notes,
        amount_total=amount_total,
        amount_advance=round(amount_total * 0.30, 2),
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        coupon_code=payload.coupon_code,
        discount_amount=discount_amount,
    )
    db.add(booking)
    db.flush()
    _notify(
        db,
        business.owner_id,
        NotificationType.booking_created,
        "New booking request",
        f"{user.full_name} requested {service.title} ({package.name}).",
    )
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=list[BookingOut])
def list_bookings(status_filter: BookingStatus | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Booking)
    if user.role == UserRole.customer:
        query = query.filter(Booking.customer_id == user.id)
    elif user.role == UserRole.business:
        business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
        if not business:
            return []
        query = query.filter(Booking.business_id == business.id)
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    return query.order_by(Booking.created_at.desc()).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)
    return booking


def _assert_booking_access(booking: Booking, user: User, db: Session):
    if user.role == UserRole.admin:
        return
    if user.role == UserRole.customer and booking.customer_id == user.id:
        return
    if user.role == UserRole.business:
        business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
        if business and booking.business_id == business.id:
            return
    raise HTTPException(403, "Not authorized for this booking")


@router.patch("/{booking_id}/status", response_model=BookingOut)
def update_booking_status(booking_id: uuid.UUID, payload: BookingStatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)

    allowed = _NEXT_STATUS.get(booking.status, set())
    if payload.status not in allowed:
        raise HTTPException(400, f"Cannot transition from {booking.status.value} to {payload.status.value}")

    booking.status = payload.status
    if payload.status == BookingStatus.cancelled:
        booking.cancellation_reason = payload.cancellation_reason
    if payload.status == BookingStatus.completed:
        booking.completed_at = datetime.utcnow()
        _notify(db, booking.customer_id, NotificationType.review_request, "How was your service?", "Please leave a review for your completed booking.")

    business = db.get(BusinessProfile, booking.business_id)
    status_messages = {
        BookingStatus.accepted: (booking.customer_id, NotificationType.booking_accepted, "Booking accepted", "Your booking request was accepted."),
        BookingStatus.rejected: (booking.customer_id, NotificationType.booking_rejected, "Booking rejected", "Your booking request was declined."),
        BookingStatus.cancelled: (
            business.owner_id if user.role == UserRole.customer else booking.customer_id,
            NotificationType.cancellation,
            "Booking cancelled",
            payload.cancellation_reason or "The booking was cancelled.",
        ),
    }
    if payload.status in status_messages:
        recipient, ntype, title, message = status_messages[payload.status]
        _notify(db, recipient, ntype, title, message)

    db.commit()
    db.refresh(booking)
    return booking

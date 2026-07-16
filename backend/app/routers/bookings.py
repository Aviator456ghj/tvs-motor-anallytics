import csv
import io
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.business_access import require_business_access, resolve_business_and_role
from app.core.database import get_db
from app.core.deps import get_current_user, require_customer
from app.models.booking import Booking, BookingEvent
from app.models.business import BusinessProfile
from app.models.catalog import Package, Service
from app.models.engagement import Coupon, Notification
from app.models.enums import BookingStatus, BusinessStaffRole, DiscountType, NotificationType, PaymentMethod, PaymentStatus, PaymentType, UserRole
from app.models.payment import Payment
from app.models.user import User
from app.schemas.booking import (
    BookingCreate,
    BookingEventOut,
    BookingListOut,
    BookingOut,
    BookingStatusUpdate,
    ManualBookingCreate,
    RefundRequest,
    TagsUpdate,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])

_NEXT_STATUS = {
    BookingStatus.requested: {BookingStatus.accepted, BookingStatus.rejected, BookingStatus.cancelled},
    BookingStatus.accepted: {BookingStatus.scheduled, BookingStatus.cancelled},
    BookingStatus.scheduled: {BookingStatus.in_progress, BookingStatus.cancelled},
    BookingStatus.in_progress: {BookingStatus.completed, BookingStatus.cancelled},
}


def _notify(db: Session, user_id: uuid.UUID, ntype: NotificationType, title: str, message: str):
    db.add(Notification(user_id=user_id, type=ntype, title=title, message=message))


def _log(db: Session, booking_id: uuid.UUID, actor_id: uuid.UUID | None, event_type: str, message: str):
    db.add(BookingEvent(booking_id=booking_id, actor_id=actor_id, event_type=event_type, message=message))


def _apply_coupon(db: Session, code: str, business: BusinessProfile, amount_total: float) -> tuple[float, Coupon]:
    coupon = db.query(Coupon).filter(Coupon.code == code, Coupon.is_active.is_(True)).first()
    if not coupon:
        raise HTTPException(400, "Invalid coupon code")
    if coupon.business_id is not None and coupon.business_id != business.id:
        raise HTTPException(400, "This coupon isn't valid for this business")
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
    return discount_amount, coupon


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
        discount_amount, _coupon = _apply_coupon(db, payload.coupon_code, business, amount_total)
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
    _log(db, booking.id, user.id, "status_change", f"Booking requested by {user.full_name}.")
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


@router.post("/manual", response_model=BookingOut, status_code=201)
def create_manual_booking(
    payload: ManualBookingCreate,
    user: User = Depends(get_current_user),
    business: BusinessProfile = Depends(require_business_access()),
    db: Session = Depends(get_db),
):
    """Business-entered booking for a phone/walk-in customer — Shopify's
    Draft Order equivalent. The customer must already have a registered
    account (looked up by email); it lands straight in `accepted` since the
    business is initiating it, not requesting approval from itself."""
    customer = db.query(User).filter(User.email == payload.customer_email, User.role == UserRole.customer).first()
    if not customer:
        raise HTTPException(404, "No customer account found with that email. They need to register first.")

    service = db.query(Service).filter(Service.id == payload.service_id, Service.business_id == business.id).first()
    if not service:
        raise HTTPException(404, "Service not found")
    package = db.query(Package).filter(Package.id == payload.package_id, Package.service_id == service.id).first()
    if not package:
        raise HTTPException(404, "Package not found")

    amount_total = float(package.price)
    commission_rate = float(business.commission_rate)

    booking = Booking(
        customer_id=customer.id,
        business_id=business.id,
        service_id=service.id,
        package_id=package.id,
        status=BookingStatus.accepted,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        service_address=payload.service_address,
        notes=payload.notes,
        amount_total=amount_total,
        amount_advance=round(amount_total * 0.30, 2),
        commission_rate=commission_rate,
        commission_amount=round(amount_total * commission_rate, 2),
        created_via="manual",
    )
    db.add(booking)
    db.flush()
    _log(db, booking.id, user.id, "status_change", f"Created manually by {user.full_name} (phone/walk-in booking).")
    _notify(
        db,
        customer.id,
        NotificationType.booking_created,
        "A booking was created for you",
        f"{business.company_name} created a booking on your behalf for {service.title} ({package.name}).",
    )
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=list[BookingListOut])
def list_bookings(
    status_filter: BookingStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    tag: str | None = None,
    business_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Booking)
    if user.role == UserRole.customer:
        query = query.filter(Booking.customer_id == user.id)
    elif user.role == UserRole.business:
        business, _role = resolve_business_and_role(user, db)
        if not business:
            return []
        query = query.filter(Booking.business_id == business.id)
    elif user.role == UserRole.admin and business_id:
        query = query.filter(Booking.business_id == business_id)

    if status_filter:
        query = query.filter(Booking.status == status_filter)
    if date_from:
        query = query.filter(Booking.created_at >= date_from)
    if date_to:
        query = query.filter(Booking.created_at <= date_to)
    if tag:
        query = query.filter(Booking.tags.ilike(f"%{tag}%"))
    if q:
        query = (
            query.join(User, User.id == Booking.customer_id)
            .join(BusinessProfile, BusinessProfile.id == Booking.business_id)
            .filter(or_(User.full_name.ilike(f"%{q}%"), BusinessProfile.company_name.ilike(f"%{q}%")))
        )

    bookings = query.order_by(Booking.created_at.desc()).all()
    items = [
        BookingListOut(
            **BookingOut.model_validate(b).model_dump(),
            customer_name=b.customer.full_name,
            business_name=b.business.company_name,
            service_title=b.service.title,
            package_name=b.package.name,
        )
        for b in bookings
    ]
    if user.role == UserRole.customer:
        for item in items:
            item.tags = None  # tags are internal business categorization, not customer-facing
    return items


@router.get("/export")
def export_bookings(
    status_filter: BookingStatus | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bookings = list_bookings(status_filter=status_filter, date_from=None, date_to=None, q=None, tag=None, business_id=None, user=user, db=db)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Booking ID", "Created", "Status", "Total", "Paid", "Refunded", "Commission", "Tags"])
    for b in bookings:
        writer.writerow([str(b.id), b.created_at.isoformat(), b.status.value, b.amount_total, b.amount_paid, b.amount_refunded, b.commission_amount, b.tags or ""])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bookings.csv"},
    )


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)
    out = BookingOut.model_validate(booking)
    if user.role == UserRole.customer:
        out.tags = None  # tags are internal business categorization, not customer-facing
    return out


def _assert_booking_access(booking: Booking, user: User, db: Session):
    if user.role == UserRole.admin:
        return
    if user.role == UserRole.customer and booking.customer_id == user.id:
        return
    if user.role == UserRole.business:
        business, _role = resolve_business_and_role(user, db)
        if business and booking.business_id == business.id:
            return
    raise HTTPException(403, "Not authorized for this booking")


_INTERNAL_ONLY_EVENT_TYPES = {"note", "tag"}


@router.get("/{booking_id}/events", response_model=list[BookingEventOut])
def get_booking_events(booking_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)
    if user.role == UserRole.customer:
        return [e for e in booking.events if e.event_type not in _INTERNAL_ONLY_EVENT_TYPES]
    return booking.events


@router.post("/{booking_id}/notes", response_model=BookingEventOut, status_code=201)
def add_booking_note(booking_id: uuid.UUID, message: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in (UserRole.business, UserRole.admin):
        raise HTTPException(403, "Only the business or an admin can add internal notes")
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)
    event = BookingEvent(booking_id=booking.id, actor_id=user.id, event_type="note", message=message)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.patch("/{booking_id}/tags", response_model=BookingOut)
def update_booking_tags(booking_id: uuid.UUID, payload: TagsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in (UserRole.business, UserRole.admin):
        raise HTTPException(403, "Only the business or an admin can tag a booking")
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)
    booking.tags = ",".join(t.strip() for t in payload.tags if t.strip()) or None
    _log(db, booking.id, user.id, "tag", f"Tags updated: {booking.tags or '(cleared)'}")
    db.commit()
    db.refresh(booking)
    return booking


@router.patch("/{booking_id}/status", response_model=BookingOut)
def update_booking_status(booking_id: uuid.UUID, payload: BookingStatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)

    allowed = _NEXT_STATUS.get(booking.status, set())
    if payload.status not in allowed:
        raise HTTPException(400, f"Cannot transition from {booking.status.value} to {payload.status.value}")

    previous = booking.status
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

    _log(db, booking.id, user.id, "status_change", f"Status changed from {previous.value} to {payload.status.value} by {user.full_name}.")

    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/refund", response_model=BookingOut)
def refund_booking(booking_id: uuid.UUID, payload: RefundRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in (UserRole.business, UserRole.admin):
        raise HTTPException(403, "Only the business or an admin can issue a refund")
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)

    refundable = float(booking.amount_paid) - float(booking.amount_refunded)
    if payload.amount <= 0 or payload.amount > refundable:
        raise HTTPException(400, f"Refund amount must be between 0 and {refundable:.2f}")

    payment = Payment(
        booking_id=booking.id,
        amount=payload.amount,
        payment_type=PaymentType.refund,
        method=PaymentMethod.wallet,
        status=PaymentStatus.refunded,
        gateway_ref=f"mock_refund_{uuid.uuid4().hex[:12]}",
    )
    db.add(payment)
    booking.amount_refunded = float(booking.amount_refunded) + payload.amount

    customer = db.get(User, booking.customer_id)
    customer.wallet_balance = float(customer.wallet_balance) + payload.amount

    _notify(db, booking.customer_id, NotificationType.refund, "Refund issued", f"₹{payload.amount:,.2f} was refunded to your wallet. Reason: {payload.reason}")
    _log(db, booking.id, user.id, "refund", f"Refunded ₹{payload.amount:,.2f} — {payload.reason}")

    db.commit()
    db.refresh(booking)
    return booking

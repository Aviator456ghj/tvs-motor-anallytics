import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.booking import Booking
from app.models.business import BusinessProfile
from app.models.engagement import Notification
from app.models.enums import NotificationType, PaymentStatus, UserRole
from app.models.payment import Payment
from app.models.user import User
from app.schemas.booking import PaymentCreate, PaymentOut

router = APIRouter(prefix="/payments", tags=["payments"])


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


@router.post("", response_model=PaymentOut, status_code=201)
def create_payment(payload: PaymentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Creates a payment record for a booking. This simulates a successful gateway
    charge synchronously — swap the `_charge_via_gateway` stub for real
    Razorpay/Stripe order+webhook flows when integrating live keys.
    """
    booking = db.get(Booking, payload.booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)

    gateway_ref = _charge_via_gateway(payload.method, payload.amount)

    payment = Payment(
        booking_id=booking.id,
        amount=payload.amount,
        payment_type=payload.payment_type,
        method=payload.method,
        status=PaymentStatus.success,
        gateway_ref=gateway_ref,
    )
    db.add(payment)
    booking.amount_paid = float(booking.amount_paid) + payload.amount
    db.add(
        Notification(
            user_id=booking.customer_id,
            type=NotificationType.payment_received,
            title="Payment successful",
            message=f"Payment of ₹{payload.amount:,.2f} received for your booking.",
        )
    )
    business = db.get(BusinessProfile, booking.business_id)
    db.add(
        Notification(
            user_id=business.owner_id,
            type=NotificationType.payment_received,
            title="Payment received",
            message=f"₹{payload.amount:,.2f} received for a booking.",
        )
    )
    db.commit()
    db.refresh(payment)
    return payment


def _charge_via_gateway(method, amount: float) -> str:
    """Stub for Razorpay/Stripe order creation + capture. Returns a mock gateway reference."""
    return f"mock_txn_{uuid.uuid4().hex[:12]}"


@router.get("/booking/{booking_id}", response_model=list[PaymentOut])
def list_payments_for_booking(booking_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    _assert_booking_access(booking, user, db)
    return db.query(Payment).filter(Payment.booking_id == booking_id).order_by(Payment.created_at).all()

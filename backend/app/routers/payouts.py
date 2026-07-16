import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.business_access import require_business_access
from app.core.database import get_db
from app.models.booking import Booking
from app.models.business import BusinessProfile
from app.models.engagement import Notification
from app.models.enums import BookingStatus, BusinessStaffRole, NotificationType, PayoutStatus
from app.models.payment import PayoutRecord
from app.schemas.payout import PayoutBalanceOut, PayoutOut, PayoutRequest

router = APIRouter(prefix="/payouts", tags=["payouts"])


def _balance(business_id: uuid.UUID, db: Session) -> dict:
    gross_paid = db.query(func.coalesce(func.sum(Booking.amount_paid), 0)).filter(Booking.business_id == business_id).scalar()
    refunded = db.query(func.coalesce(func.sum(Booking.amount_refunded), 0)).filter(Booking.business_id == business_id).scalar()
    commission = (
        db.query(func.coalesce(func.sum(Booking.commission_amount), 0))
        .filter(Booking.business_id == business_id, Booking.status == BookingStatus.completed)
        .scalar()
    )
    paid_out = (
        db.query(func.coalesce(func.sum(PayoutRecord.amount), 0))
        .filter(PayoutRecord.business_id == business_id, PayoutRecord.status == PayoutStatus.paid)
        .scalar()
    )
    net_lifetime = float(gross_paid) - float(refunded) - float(commission)
    available = round(net_lifetime - float(paid_out), 2)
    return {
        "available_balance": max(available, 0),
        "lifetime_gross": float(gross_paid),
        "lifetime_commission": float(commission),
        "lifetime_refunded": float(refunded),
        "lifetime_paid_out": float(paid_out),
    }


@router.get("/me/balance", response_model=PayoutBalanceOut)
def my_balance(business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)), db: Session = Depends(get_db)):
    return _balance(business.id, db)


@router.get("/me", response_model=list[PayoutOut])
def my_payouts(business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)), db: Session = Depends(get_db)):
    return db.query(PayoutRecord).filter(PayoutRecord.business_id == business.id).order_by(PayoutRecord.created_at.desc()).all()


@router.post("/me/request", response_model=PayoutOut, status_code=201)
def request_payout(
    payload: PayoutRequest,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.owner)),
    db: Session = Depends(get_db),
):
    """
    Simulates an instant payout (marked `paid` immediately) since there's no
    real bank-transfer rail wired up. See docs/ROADMAP.md for connecting
    Razorpay Route / Stripe Connect transfers.
    """
    bal = _balance(business.id, db)
    if payload.amount <= 0 or payload.amount > bal["available_balance"]:
        raise HTTPException(400, f"Requested amount must be between 0 and {bal['available_balance']:.2f}")

    payout = PayoutRecord(
        business_id=business.id,
        amount=payload.amount,
        status=PayoutStatus.paid,
        reference=f"payout_{uuid.uuid4().hex[:12]}",
    )
    db.add(payout)
    db.add(
        Notification(
            user_id=business.owner_id,
            type=NotificationType.payment_received,
            title="Payout sent",
            message=f"₹{payload.amount:,.2f} was paid out to your linked bank account.",
        )
    )
    db.commit()
    db.refresh(payout)
    return payout

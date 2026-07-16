import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.business_access import require_business_access
from app.core.database import get_db
from app.models.booking import Booking
from app.models.business import BusinessPayoutAccount, BusinessProfile
from app.models.engagement import Notification
from app.models.enums import BookingStatus, BusinessStaffRole, NotificationType, PaymentType, PayoutStatus
from app.models.payment import Payment, PayoutRecord
from app.schemas.payout import PayoutBalanceOut, PayoutOut, PayoutRequest, TransactionOut

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
    if not db.query(BusinessPayoutAccount).filter(BusinessPayoutAccount.business_id == business.id).first():
        raise HTTPException(400, "Add a payout bank account in Settings before requesting a payout.")
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


@router.get("/me/transactions", response_model=list[TransactionOut])
def my_transactions(business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)), db: Session = Depends(get_db)):
    """Unified chronological ledger — payments in, refunds out, payouts out —
    with a running balance. Shopify's Finance > Payouts transaction list."""
    payments = (
        db.query(Payment)
        .join(Booking, Booking.id == Payment.booking_id)
        .filter(Booking.business_id == business.id)
        .all()
    )
    payouts = db.query(PayoutRecord).filter(PayoutRecord.business_id == business.id).all()

    rows = []
    for p in payments:
        is_refund = p.payment_type == PaymentType.refund
        rows.append({
            "date": p.created_at,
            "type": "refund" if is_refund else "payment",
            "description": f"{'Refund' if is_refund else 'Payment'} — {p.method.value.upper()} — {p.gateway_ref}",
            "amount": -float(p.amount) if is_refund else float(p.amount),
        })
    for po in payouts:
        rows.append({
            "date": po.created_at,
            "type": "payout",
            "description": f"Payout — {po.reference}",
            "amount": -float(po.amount),
        })

    rows.sort(key=lambda r: r["date"])
    balance = 0.0
    for r in rows:
        balance += r["amount"]
        r["running_balance"] = round(balance, 2)
    rows.reverse()
    return rows

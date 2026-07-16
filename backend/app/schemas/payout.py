import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import PayoutStatus


class PayoutRequest(BaseModel):
    amount: float


class PayoutOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    amount: float
    status: PayoutStatus
    reference: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PayoutBalanceOut(BaseModel):
    available_balance: float
    lifetime_gross: float
    lifetime_commission: float
    lifetime_refunded: float
    lifetime_paid_out: float


class TransactionOut(BaseModel):
    date: datetime
    type: str  # payment | refund | payout
    description: str
    amount: float  # signed: positive = money in, negative = money out
    running_balance: float

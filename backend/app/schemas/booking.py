import uuid
from datetime import date, datetime, time

from pydantic import BaseModel

from app.models.enums import BookingStatus, PaymentMethod, PaymentType


class BookingCreate(BaseModel):
    business_id: uuid.UUID
    service_id: uuid.UUID
    package_id: uuid.UUID
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    service_address: str | None = None
    notes: str | None = None
    coupon_code: str | None = None


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    cancellation_reason: str | None = None


class BookingOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    business_id: uuid.UUID
    service_id: uuid.UUID
    package_id: uuid.UUID
    status: BookingStatus
    scheduled_date: date | None
    scheduled_time: time | None
    service_address: str | None
    notes: str | None
    amount_total: float
    amount_advance: float
    amount_paid: float
    commission_amount: float
    discount_amount: float
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    booking_id: uuid.UUID
    payment_type: PaymentType
    method: PaymentMethod
    amount: float


class PaymentOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: float
    payment_type: PaymentType
    method: PaymentMethod
    status: str
    gateway: str
    gateway_ref: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    booking_id: uuid.UUID
    rating: int
    comment: str | None = None


class ReviewOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    business_id: uuid.UUID
    rating: int
    comment: str | None
    provider_response: str | None
    is_flagged: bool
    created_at: datetime

    model_config = {"from_attributes": True}

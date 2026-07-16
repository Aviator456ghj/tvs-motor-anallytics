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


class ManualBookingCreate(BaseModel):
    customer_email: str
    service_id: uuid.UUID
    package_id: uuid.UUID
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    service_address: str | None = None
    notes: str | None = None


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    cancellation_reason: str | None = None


class TagsUpdate(BaseModel):
    tags: list[str]


class RefundRequest(BaseModel):
    amount: float
    reason: str


class BookingEventOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    actor_id: uuid.UUID | None
    event_type: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


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
    amount_refunded: float
    commission_amount: float
    discount_amount: float
    tags: str | None
    created_via: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingListOut(BookingOut):
    """BookingOut plus joined display fields, for the Orders-style list views."""

    customer_name: str
    business_name: str
    service_title: str
    package_name: str


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

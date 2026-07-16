import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DiscountType, NotificationType


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    business_id: uuid.UUID
    message: str
    booking_id: uuid.UUID | None = None


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    sender_id: uuid.UUID
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatThreadOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    business_id: uuid.UUID
    booking_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CouponCreate(BaseModel):
    code: str
    discount_type: DiscountType
    discount_value: float
    category_id: uuid.UUID | None = None
    min_order_value: float = 0
    max_discount: float | None = None
    usage_limit: int | None = None
    valid_to: datetime | None = None


class CouponOut(CouponCreate):
    id: uuid.UUID
    usage_count: int
    is_active: bool

    model_config = {"from_attributes": True}


class WishlistOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SupportTicketCreate(BaseModel):
    subject: str
    message: str
    priority: str = "normal"


class SupportTicketOut(SupportTicketCreate):
    id: uuid.UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CmsPageCreate(BaseModel):
    slug: str
    title: str
    content: str
    is_published: bool = True


class CmsPageOut(CmsPageCreate):
    id: uuid.UUID
    updated_at: datetime

    model_config = {"from_attributes": True}

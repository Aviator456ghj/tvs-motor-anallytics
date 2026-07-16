import uuid
from datetime import date, datetime, time

from pydantic import BaseModel

from app.models.enums import PortfolioType


class CategoryOut(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    slug: str
    icon: str | None
    description: str | None
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class CategoryTreeOut(CategoryOut):
    children: list["CategoryTreeOut"] = []


class CategoryCreate(BaseModel):
    name: str
    slug: str
    parent_id: uuid.UUID | None = None
    icon: str | None = None
    description: str | None = None
    sort_order: int = 0


class PackageBase(BaseModel):
    name: str
    price: float
    duration_minutes: int | None = None
    description: str | None = None
    deliverables: str | None = None


class PackageCreate(PackageBase):
    pass


class PackageOut(PackageBase):
    id: uuid.UUID
    service_id: uuid.UUID
    is_active: bool

    model_config = {"from_attributes": True}


class ServiceBase(BaseModel):
    title: str
    category_id: uuid.UUID
    description: str | None = None
    is_home_service: bool = False
    is_instant_booking: bool = False


class ServiceCreate(ServiceBase):
    pass


class ServiceOut(ServiceBase):
    id: uuid.UUID
    business_id: uuid.UUID
    is_active: bool
    packages: list[PackageOut] = []

    model_config = {"from_attributes": True}


class PortfolioItemCreate(BaseModel):
    item_type: PortfolioType
    url: str
    thumbnail_url: str | None = None
    caption: str | None = None


class PortfolioItemOut(PortfolioItemCreate):
    id: uuid.UUID
    business_id: uuid.UUID

    model_config = {"from_attributes": True}


class AvailabilitySlotCreate(BaseModel):
    date: date
    start_time: time
    end_time: time
    capacity: int = 1


class AvailabilitySlotOut(AvailabilitySlotCreate):
    id: uuid.UUID
    business_id: uuid.UUID
    booked_count: int
    is_blocked: bool

    model_config = {"from_attributes": True}

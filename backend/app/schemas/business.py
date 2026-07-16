import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.enums import BusinessStaffRole, KycStatus, SubscriptionPlan
from app.schemas.booking import BookingListOut
from app.schemas.catalog import PortfolioItemOut, ServiceOut


class BusinessCreate(BaseModel):
    company_name: str
    tagline: str | None = None
    description: str | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None
    experience_years: int = 0
    languages: str | None = None
    offers_home_service: bool = False
    offers_instant_booking: bool = False
    category_ids: list[uuid.UUID] = []


class BusinessUpdate(BaseModel):
    company_name: str | None = None
    tagline: str | None = None
    description: str | None = None
    logo_url: str | None = None
    cover_image_url: str | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None
    experience_years: int | None = None
    languages: str | None = None
    offers_home_service: bool | None = None
    offers_instant_booking: bool | None = None


class BusinessOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    company_name: str
    slug: str
    tagline: str | None
    description: str | None
    logo_url: str | None
    cover_image_url: str | None
    city: str | None
    state: str | None
    experience_years: int
    offers_home_service: bool
    offers_instant_booking: bool
    is_verified: bool
    kyc_status: KycStatus
    is_approved: bool
    rating_avg: float
    rating_count: int
    subscription_plan: SubscriptionPlan

    model_config = {"from_attributes": True}


class BusinessDetailOut(BusinessOut):
    services: list[ServiceOut] = []
    portfolio_items: list[PortfolioItemOut] = []


class EmployeeCreate(BaseModel):
    name: str
    role_title: str | None = None
    phone: str | None = None
    email: str | None = None


class EmployeeOut(EmployeeCreate):
    id: uuid.UUID
    business_id: uuid.UUID

    model_config = {"from_attributes": True}


class DocumentCreate(BaseModel):
    doc_type: str
    file_url: str


class DocumentOut(DocumentCreate):
    id: uuid.UUID
    business_id: uuid.UUID
    status: str

    model_config = {"from_attributes": True}


class StaffInvite(BaseModel):
    email: EmailStr
    role: BusinessStaffRole = BusinessStaffRole.staff


class StaffMemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    role: BusinessStaffRole
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerSummaryOut(BaseModel):
    customer_id: uuid.UUID
    full_name: str
    email: str
    city: str | None
    order_count: int
    total_spent: float
    last_order_at: datetime


class CustomerDetailOut(CustomerSummaryOut):
    bookings: list[BookingListOut] = []

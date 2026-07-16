import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from slugify import slugify
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.business_access import require_business_access
from app.core.database import get_db
from app.core.deps import require_business
from app.models.booking import Booking
from app.models.business import BusinessDocument, BusinessLocation, BusinessPayoutAccount, BusinessProfile, BusinessStaff, Employee
from app.models.catalog import BusinessCategory, Category
from app.models.engagement import Coupon, Notification
from app.models.enums import BusinessStaffRole, DiscountType, NotificationType, UserRole
from app.models.user import User
from app.schemas.booking import BookingListOut, BookingOut
from app.schemas.business import (
    BusinessCreate,
    BusinessDetailOut,
    BusinessOut,
    BusinessUpdate,
    CustomerDetailOut,
    CustomerSummaryOut,
    DocumentCreate,
    DocumentOut,
    EmployeeCreate,
    EmployeeOut,
    LocationCreate,
    LocationOut,
    NotificationPreferencesUpdate,
    PayoutAccountCreate,
    PayoutAccountOut,
    StaffInvite,
    StaffMemberOut,
)
from app.schemas.engagement import CouponCreate, CouponOut

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessOut, status_code=201)
def create_business(payload: BusinessCreate, user: User = Depends(require_business), db: Session = Depends(get_db)):
    if db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first():
        raise HTTPException(400, "Business profile already exists for this account")
    slug_base = slugify(payload.company_name)
    slug = slug_base
    counter = 1
    while db.query(BusinessProfile).filter(BusinessProfile.slug == slug).first():
        counter += 1
        slug = f"{slug_base}-{counter}"

    data = payload.model_dump(exclude={"category_ids"})
    business = BusinessProfile(owner_id=user.id, slug=slug, **data)
    db.add(business)
    db.flush()
    for cat_id in payload.category_ids:
        db.add(BusinessCategory(business_id=business.id, category_id=cat_id))
    db.commit()
    db.refresh(business)
    return business


@router.get("/me", response_model=BusinessDetailOut)
def get_my_business(business: BusinessProfile = Depends(require_business_access())):
    return business


@router.patch("/me", response_model=BusinessOut)
def update_my_business(
    payload: BusinessUpdate,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.owner)),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(business, field, value)
    db.commit()
    db.refresh(business)
    return business


@router.get("/search", response_model=list[BusinessOut])
def search_businesses(
    q: str | None = None,
    category_slug: str | None = None,
    city: str | None = None,
    min_rating: float | None = None,
    verified_only: bool = False,
    instant_booking: bool = False,
    home_service: bool = False,
    sort: str = Query("rating", pattern="^(rating|experience|newest)$"),
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(BusinessProfile).filter(BusinessProfile.is_approved.is_(True))
    if q:
        query = query.filter(or_(BusinessProfile.company_name.ilike(f"%{q}%"), BusinessProfile.description.ilike(f"%{q}%")))
    if category_slug:
        query = (
            query.join(BusinessCategory, BusinessCategory.business_id == BusinessProfile.id)
            .join(Category, Category.id == BusinessCategory.category_id)
            .filter(Category.slug == category_slug)
        )
    if city:
        query = query.filter(BusinessProfile.city.ilike(f"%{city}%"))
    if min_rating:
        query = query.filter(BusinessProfile.rating_avg >= min_rating)
    if verified_only:
        query = query.filter(BusinessProfile.is_verified.is_(True))
    if instant_booking:
        query = query.filter(BusinessProfile.offers_instant_booking.is_(True))
    if home_service:
        query = query.filter(BusinessProfile.offers_home_service.is_(True))

    if sort == "rating":
        query = query.order_by(BusinessProfile.rating_avg.desc())
    elif sort == "experience":
        query = query.order_by(BusinessProfile.experience_years.desc())
    else:
        query = query.order_by(BusinessProfile.created_at.desc())

    return query.offset(offset).limit(limit).all()


@router.get("/{slug}", response_model=BusinessDetailOut)
def get_business(slug: str, db: Session = Depends(get_db)):
    business = db.query(BusinessProfile).filter(BusinessProfile.slug == slug, BusinessProfile.is_approved.is_(True)).first()
    if not business:
        raise HTTPException(404, "Business not found")
    return business


# --- Employees (non-login team roster) ---
@router.post("/me/employees", response_model=EmployeeOut, status_code=201)
def add_employee(
    payload: EmployeeCreate,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    employee = Employee(business_id=business.id, **payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/me/employees", response_model=list[EmployeeOut])
def list_employees(business: BusinessProfile = Depends(require_business_access()), db: Session = Depends(get_db)):
    return db.query(Employee).filter(Employee.business_id == business.id).all()


@router.delete("/me/employees/{employee_id}", status_code=204)
def remove_employee(
    employee_id: uuid.UUID,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.business_id == business.id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    db.delete(employee)
    db.commit()


# --- KYC documents (owner-only: compliance-sensitive) ---
@router.post("/me/documents", response_model=DocumentOut, status_code=201)
def upload_document(
    payload: DocumentCreate,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.owner)),
    db: Session = Depends(get_db),
):
    doc = BusinessDocument(business_id=business.id, **payload.model_dump())
    db.add(doc)
    business.kyc_status = "submitted"
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/me/documents", response_model=list[DocumentOut])
def list_documents(business: BusinessProfile = Depends(require_business_access()), db: Session = Depends(get_db)):
    return db.query(BusinessDocument).filter(BusinessDocument.business_id == business.id).all()


# --- Staff accounts (login accounts with a permission tier on this business) ---
@router.get("/me/staff", response_model=list[StaffMemberOut])
def list_staff(business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)), db: Session = Depends(get_db)):
    rows = db.query(BusinessStaff).filter(BusinessStaff.business_id == business.id).all()
    out = [
        StaffMemberOut(id=r.id, user_id=r.user_id, full_name=r.user.full_name, email=r.user.email, role=r.role, created_at=r.created_at)
        for r in rows
    ]
    owner = business.owner
    out.insert(0, StaffMemberOut(id=business.id, user_id=owner.id, full_name=owner.full_name, email=owner.email, role=BusinessStaffRole.owner, created_at=business.created_at))
    return out


@router.post("/me/staff", response_model=StaffMemberOut, status_code=201)
def invite_staff(
    payload: StaffInvite,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.owner)),
    db: Session = Depends(get_db),
):
    invitee = db.query(User).filter(User.email == payload.email).first()
    if not invitee:
        raise HTTPException(404, "No account found with that email. Ask them to register as a Business account first.")
    if invitee.role != UserRole.business:
        raise HTTPException(400, "Only accounts registered with the Business role can be added as staff.")
    if invitee.id == business.owner_id:
        raise HTTPException(400, "This user already owns the business.")
    existing = db.query(BusinessStaff).filter(BusinessStaff.business_id == business.id, BusinessStaff.user_id == invitee.id).first()
    if existing:
        existing.role = payload.role
        db.commit()
        db.refresh(existing)
        row = existing
    else:
        row = BusinessStaff(business_id=business.id, user_id=invitee.id, role=payload.role)
        db.add(row)
        db.commit()
        db.refresh(row)
    db.add(
        Notification(
            user_id=invitee.id,
            type=NotificationType.system,
            title="You've been added to a business team",
            message=f"You now have {payload.role.value} access to {business.company_name}.",
        )
    )
    db.commit()
    return StaffMemberOut(id=row.id, user_id=invitee.id, full_name=invitee.full_name, email=invitee.email, role=row.role, created_at=row.created_at)


@router.delete("/me/staff/{staff_id}", status_code=204)
def remove_staff(
    staff_id: uuid.UUID,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.owner)),
    db: Session = Depends(get_db),
):
    row = db.query(BusinessStaff).filter(BusinessStaff.id == staff_id, BusinessStaff.business_id == business.id).first()
    if not row:
        raise HTTPException(404, "Staff member not found")
    db.delete(row)
    db.commit()


# --- Customers (customer 360 for this business) ---
@router.get("/me/customers", response_model=list[CustomerSummaryOut])
def list_business_customers(
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Booking.customer_id,
            func.count(Booking.id),
            func.coalesce(func.sum(Booking.amount_paid), 0),
            func.max(Booking.created_at),
        )
        .filter(Booking.business_id == business.id)
        .group_by(Booking.customer_id)
        .order_by(func.max(Booking.created_at).desc())
        .all()
    )
    out = []
    for customer_id, order_count, total_spent, last_order_at in rows:
        customer = db.get(User, customer_id)
        out.append(
            CustomerSummaryOut(
                customer_id=customer_id,
                full_name=customer.full_name,
                email=customer.email,
                city=customer.city,
                order_count=order_count,
                total_spent=float(total_spent),
                last_order_at=last_order_at,
            )
        )
    return out


@router.get("/me/customers/{customer_id}", response_model=CustomerDetailOut)
def get_business_customer(
    customer_id: uuid.UUID,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    customer = db.get(User, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    bookings = (
        db.query(Booking)
        .filter(Booking.business_id == business.id, Booking.customer_id == customer_id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    if not bookings:
        raise HTTPException(404, "This customer has no bookings with your business")

    booking_items = [
        BookingListOut(
            **BookingOut.model_validate(b).model_dump(),
            customer_name=customer.full_name,
            business_name=business.company_name,
            service_title=b.service.title,
            package_name=b.package.name,
        )
        for b in bookings
    ]
    return CustomerDetailOut(
        customer_id=customer.id,
        full_name=customer.full_name,
        email=customer.email,
        city=customer.city,
        order_count=len(bookings),
        total_spent=sum(float(b.amount_paid) for b in bookings),
        last_order_at=bookings[0].created_at,
        bookings=booking_items,
    )


# --- Discounts (business-scoped, unlike admin's platform-wide coupons) ---
@router.get("/me/discounts", response_model=list[CouponOut])
def list_my_discounts(business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)), db: Session = Depends(get_db)):
    return db.query(Coupon).filter(Coupon.business_id == business.id).order_by(Coupon.valid_from.desc()).all()


@router.post("/me/discounts", response_model=CouponOut, status_code=201)
def create_my_discount(
    payload: CouponCreate,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    if db.query(Coupon).filter(Coupon.code == payload.code).first():
        raise HTTPException(400, "Coupon code already exists")
    coupon = Coupon(business_id=business.id, **payload.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.patch("/me/discounts/{coupon_id}/deactivate", response_model=CouponOut)
def deactivate_my_discount(
    coupon_id: uuid.UUID,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id, Coupon.business_id == business.id).first()
    if not coupon:
        raise HTTPException(404, "Discount not found")
    coupon.is_active = False
    db.commit()
    db.refresh(coupon)
    return coupon


# --- Locations (studio address / home-service radius) ---
@router.get("/me/locations", response_model=list[LocationOut])
def list_locations(business: BusinessProfile = Depends(require_business_access()), db: Session = Depends(get_db)):
    return db.query(BusinessLocation).filter(BusinessLocation.business_id == business.id).order_by(BusinessLocation.created_at).all()


@router.post("/me/locations", response_model=LocationOut, status_code=201)
def create_location(
    payload: LocationCreate,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    if payload.is_primary:
        db.query(BusinessLocation).filter(BusinessLocation.business_id == business.id).update({"is_primary": False})
    location = BusinessLocation(business_id=business.id, **payload.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.delete("/me/locations/{location_id}", status_code=204)
def delete_location(
    location_id: uuid.UUID,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.manager)),
    db: Session = Depends(get_db),
):
    location = db.query(BusinessLocation).filter(BusinessLocation.id == location_id, BusinessLocation.business_id == business.id).first()
    if not location:
        raise HTTPException(404, "Location not found")
    db.delete(location)
    db.commit()


# --- Payout account (bank details payouts are sent to) ---
@router.get("/me/payout-account", response_model=PayoutAccountOut | None)
def get_payout_account(business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.owner)), db: Session = Depends(get_db)):
    return db.query(BusinessPayoutAccount).filter(BusinessPayoutAccount.business_id == business.id).first()


@router.put("/me/payout-account", response_model=PayoutAccountOut)
def set_payout_account(
    payload: PayoutAccountCreate,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.owner)),
    db: Session = Depends(get_db),
):
    account = db.query(BusinessPayoutAccount).filter(BusinessPayoutAccount.business_id == business.id).first()
    last4 = payload.account_number[-4:]
    fields = dict(
        account_holder_name=payload.account_holder_name,
        bank_name=payload.bank_name,
        account_number_last4=last4,
        ifsc_code=payload.ifsc_code,
        upi_id=payload.upi_id,
        is_verified=False,  # any change requires re-verification
    )
    if account:
        for k, v in fields.items():
            setattr(account, k, v)
    else:
        account = BusinessPayoutAccount(business_id=business.id, **fields)
        db.add(account)
    db.commit()
    db.refresh(account)
    return account


# --- Notification preferences ---
@router.put("/me/notification-preferences", response_model=BusinessOut)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    business: BusinessProfile = Depends(require_business_access(BusinessStaffRole.owner)),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump().items():
        setattr(business, field, value)
    db.commit()
    db.refresh(business)
    return business

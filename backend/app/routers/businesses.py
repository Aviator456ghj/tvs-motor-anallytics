import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from slugify import slugify
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_business
from app.models.business import BusinessDocument, BusinessProfile, Employee
from app.models.catalog import BusinessCategory, Category
from app.models.user import User
from app.schemas.business import (
    BusinessCreate,
    BusinessDetailOut,
    BusinessOut,
    BusinessUpdate,
    DocumentCreate,
    DocumentOut,
    EmployeeCreate,
    EmployeeOut,
)

router = APIRouter(prefix="/businesses", tags=["businesses"])


def _get_own_business(user: User, db: Session) -> BusinessProfile:
    business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
    if not business:
        raise HTTPException(404, "Business profile not found for this account")
    return business


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
def get_my_business(user: User = Depends(require_business), db: Session = Depends(get_db)):
    return _get_own_business(user, db)


@router.patch("/me", response_model=BusinessOut)
def update_my_business(payload: BusinessUpdate, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _get_own_business(user, db)
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


# --- Employees ---
@router.post("/me/employees", response_model=EmployeeOut, status_code=201)
def add_employee(payload: EmployeeCreate, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _get_own_business(user, db)
    employee = Employee(business_id=business.id, **payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/me/employees", response_model=list[EmployeeOut])
def list_employees(user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _get_own_business(user, db)
    return db.query(Employee).filter(Employee.business_id == business.id).all()


@router.delete("/me/employees/{employee_id}", status_code=204)
def remove_employee(employee_id: uuid.UUID, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _get_own_business(user, db)
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.business_id == business.id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    db.delete(employee)
    db.commit()


# --- KYC documents ---
@router.post("/me/documents", response_model=DocumentOut, status_code=201)
def upload_document(payload: DocumentCreate, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _get_own_business(user, db)
    doc = BusinessDocument(business_id=business.id, **payload.model_dump())
    db.add(doc)
    business.kyc_status = "submitted"
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/me/documents", response_model=list[DocumentOut])
def list_documents(user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _get_own_business(user, db)
    return db.query(BusinessDocument).filter(BusinessDocument.business_id == business.id).all()

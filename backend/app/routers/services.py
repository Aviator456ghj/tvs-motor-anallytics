import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_business
from app.models.business import BusinessProfile
from app.models.catalog import Package, PortfolioItem, Service
from app.models.user import User
from app.schemas.catalog import (
    PackageCreate,
    PackageOut,
    PortfolioItemCreate,
    PortfolioItemOut,
    ServiceCreate,
    ServiceOut,
)

router = APIRouter(tags=["services"])


def _own_business(user: User, db: Session) -> BusinessProfile:
    business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
    if not business:
        raise HTTPException(404, "Business profile not found")
    return business


def _own_service(service_id: uuid.UUID, business_id: uuid.UUID, db: Session) -> Service:
    service = db.query(Service).filter(Service.id == service_id, Service.business_id == business_id).first()
    if not service:
        raise HTTPException(404, "Service not found")
    return service


@router.get("/businesses/{slug}/services", response_model=list[ServiceOut])
def list_public_services(slug: str, db: Session = Depends(get_db)):
    business = db.query(BusinessProfile).filter(BusinessProfile.slug == slug).first()
    if not business:
        raise HTTPException(404, "Business not found")
    return db.query(Service).filter(Service.business_id == business.id, Service.is_active.is_(True)).all()


@router.post("/services", response_model=ServiceOut, status_code=201)
def create_service(payload: ServiceCreate, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _own_business(user, db)
    service = Service(business_id=business.id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.get("/services/me", response_model=list[ServiceOut])
def list_my_services(user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _own_business(user, db)
    return db.query(Service).filter(Service.business_id == business.id).all()


@router.delete("/services/{service_id}", status_code=204)
def delete_service(service_id: uuid.UUID, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _own_business(user, db)
    service = _own_service(service_id, business.id, db)
    service.is_active = False
    db.commit()


@router.post("/services/{service_id}/packages", response_model=PackageOut, status_code=201)
def create_package(service_id: uuid.UUID, payload: PackageCreate, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _own_business(user, db)
    _own_service(service_id, business.id, db)
    package = Package(service_id=service_id, **payload.model_dump())
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@router.patch("/packages/{package_id}", response_model=PackageOut)
def update_package(package_id: uuid.UUID, payload: PackageCreate, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _own_business(user, db)
    package = (
        db.query(Package)
        .join(Service, Service.id == Package.service_id)
        .filter(Package.id == package_id, Service.business_id == business.id)
        .first()
    )
    if not package:
        raise HTTPException(404, "Package not found")
    for field, value in payload.model_dump().items():
        setattr(package, field, value)
    db.commit()
    db.refresh(package)
    return package


@router.delete("/packages/{package_id}", status_code=204)
def delete_package(package_id: uuid.UUID, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _own_business(user, db)
    package = (
        db.query(Package)
        .join(Service, Service.id == Package.service_id)
        .filter(Package.id == package_id, Service.business_id == business.id)
        .first()
    )
    if not package:
        raise HTTPException(404, "Package not found")
    package.is_active = False
    db.commit()


# --- Portfolio ---
@router.get("/businesses/{slug}/portfolio", response_model=list[PortfolioItemOut])
def list_public_portfolio(slug: str, db: Session = Depends(get_db)):
    business = db.query(BusinessProfile).filter(BusinessProfile.slug == slug).first()
    if not business:
        raise HTTPException(404, "Business not found")
    return db.query(PortfolioItem).filter(PortfolioItem.business_id == business.id).order_by(PortfolioItem.sort_order).all()


@router.post("/portfolio", response_model=PortfolioItemOut, status_code=201)
def add_portfolio_item(payload: PortfolioItemCreate, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _own_business(user, db)
    item = PortfolioItem(business_id=business.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/portfolio/{item_id}", status_code=204)
def delete_portfolio_item(item_id: uuid.UUID, user: User = Depends(require_business), db: Session = Depends(get_db)):
    business = _own_business(user, db)
    item = db.query(PortfolioItem).filter(PortfolioItem.id == item_id, PortfolioItem.business_id == business.id).first()
    if not item:
        raise HTTPException(404, "Portfolio item not found")
    db.delete(item)
    db.commit()

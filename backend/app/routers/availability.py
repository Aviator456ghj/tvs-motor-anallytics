import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.business_access import require_business_access
from app.core.database import get_db
from app.models.business import BusinessProfile
from app.models.catalog import AvailabilitySlot
from app.schemas.catalog import AvailabilitySlotCreate, AvailabilitySlotOut

router = APIRouter(tags=["availability"])


@router.get("/businesses/{slug}/availability", response_model=list[AvailabilitySlotOut])
def public_availability(slug: str, from_date: date | None = None, db: Session = Depends(get_db)):
    business = db.query(BusinessProfile).filter(BusinessProfile.slug == slug).first()
    if not business:
        raise HTTPException(404, "Business not found")
    query = db.query(AvailabilitySlot).filter(AvailabilitySlot.business_id == business.id, AvailabilitySlot.is_blocked.is_(False))
    if from_date:
        query = query.filter(AvailabilitySlot.date >= from_date)
    return query.order_by(AvailabilitySlot.date, AvailabilitySlot.start_time).all()


@router.post("/availability", response_model=AvailabilitySlotOut, status_code=201)
def create_slot(
    payload: AvailabilitySlotCreate,
    business: BusinessProfile = Depends(require_business_access()),
    db: Session = Depends(get_db),
):
    slot = AvailabilitySlot(business_id=business.id, **payload.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.get("/availability/me", response_model=list[AvailabilitySlotOut])
def list_my_availability(business: BusinessProfile = Depends(require_business_access()), db: Session = Depends(get_db)):
    return db.query(AvailabilitySlot).filter(AvailabilitySlot.business_id == business.id).order_by(AvailabilitySlot.date).all()


@router.patch("/availability/{slot_id}/block", response_model=AvailabilitySlotOut)
def block_slot(
    slot_id: uuid.UUID,
    business: BusinessProfile = Depends(require_business_access()),
    db: Session = Depends(get_db),
):
    slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id, AvailabilitySlot.business_id == business.id).first()
    if not slot:
        raise HTTPException(404, "Slot not found")
    slot.is_blocked = True
    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/availability/{slot_id}", status_code=204)
def delete_slot(
    slot_id: uuid.UUID,
    business: BusinessProfile = Depends(require_business_access()),
    db: Session = Depends(get_db),
):
    slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id, AvailabilitySlot.business_id == business.id).first()
    if not slot:
        raise HTTPException(404, "Slot not found")
    db.delete(slot)
    db.commit()

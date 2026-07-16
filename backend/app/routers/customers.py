import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_customer
from app.models.business import BusinessProfile
from app.models.engagement import SupportTicket, Wishlist
from app.models.user import User
from app.schemas.business import BusinessOut
from app.schemas.engagement import SupportTicketCreate, SupportTicketOut, WishlistOut

router = APIRouter(tags=["customers"])


@router.post("/wishlist/{business_id}", response_model=WishlistOut, status_code=201)
def add_to_wishlist(business_id: uuid.UUID, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    if not db.get(BusinessProfile, business_id):
        raise HTTPException(404, "Business not found")
    existing = db.query(Wishlist).filter(Wishlist.customer_id == user.id, Wishlist.business_id == business_id).first()
    if existing:
        return existing
    item = Wishlist(customer_id=user.id, business_id=business_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/wishlist", response_model=list[BusinessOut])
def list_wishlist(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    return (
        db.query(BusinessProfile)
        .join(Wishlist, Wishlist.business_id == BusinessProfile.id)
        .filter(Wishlist.customer_id == user.id)
        .all()
    )


@router.delete("/wishlist/{business_id}", status_code=204)
def remove_from_wishlist(business_id: uuid.UUID, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    db.query(Wishlist).filter(Wishlist.customer_id == user.id, Wishlist.business_id == business_id).delete()
    db.commit()


@router.post("/support-tickets", response_model=SupportTicketOut, status_code=201)
def create_ticket(payload: SupportTicketCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    ticket = SupportTicket(user_id=user.id, **payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/support-tickets/me", response_model=list[SupportTicketOut])
def my_tickets(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    return db.query(SupportTicket).filter(SupportTicket.user_id == user.id).order_by(SupportTicket.created_at.desc()).all()

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.booking import Booking
from app.models.business import BusinessDocument, BusinessProfile
from app.models.engagement import CmsPage, Notification, SupportTicket
from app.models.enums import BookingStatus, DocumentStatus, KycStatus, NotificationType
from app.models.payment import Payment
from app.models.user import User
from app.schemas.business import BusinessOut, DocumentOut
from app.schemas.engagement import CmsPageCreate, CmsPageOut, SupportTicketOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/dashboard")
def dashboard_summary(db: Session = Depends(get_db)):
    total_businesses = db.query(func.count(BusinessProfile.id)).scalar()
    pending_approvals = db.query(func.count(BusinessProfile.id)).filter(BusinessProfile.is_approved.is_(False)).scalar()
    total_customers = db.query(func.count(User.id)).filter(User.role == "customer").scalar()
    total_bookings = db.query(func.count(Booking.id)).scalar()
    completed_bookings = db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.completed).scalar()
    gross_revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    commission_revenue = db.query(func.coalesce(func.sum(Booking.commission_amount), 0)).filter(Booking.status == BookingStatus.completed).scalar()
    open_tickets = db.query(func.count(SupportTicket.id)).filter(SupportTicket.status == "open").scalar()

    since = datetime.utcnow() - timedelta(days=30)
    bookings_30d = db.query(func.count(Booking.id)).filter(Booking.created_at >= since).scalar()

    return {
        "total_businesses": total_businesses,
        "pending_approvals": pending_approvals,
        "total_customers": total_customers,
        "total_bookings": total_bookings,
        "completed_bookings": completed_bookings,
        "gross_revenue": float(gross_revenue),
        "commission_revenue": float(commission_revenue),
        "open_support_tickets": open_tickets,
        "bookings_last_30_days": bookings_30d,
    }


@router.get("/businesses", response_model=list[BusinessOut])
def list_all_businesses(pending_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(BusinessProfile)
    if pending_only:
        query = query.filter(BusinessProfile.is_approved.is_(False))
    return query.order_by(BusinessProfile.created_at.desc()).all()


@router.patch("/businesses/{business_id}/approve", response_model=BusinessOut)
def approve_business(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(BusinessProfile, business_id)
    if not business:
        raise HTTPException(404, "Business not found")
    business.is_approved = True
    db.add(
        Notification(
            user_id=business.owner_id,
            type=NotificationType.system,
            title="Business approved",
            message="Your business profile has been approved and is now live.",
        )
    )
    db.commit()
    db.refresh(business)
    return business


@router.patch("/businesses/{business_id}/suspend", response_model=BusinessOut)
def suspend_business(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(BusinessProfile, business_id)
    if not business:
        raise HTTPException(404, "Business not found")
    business.is_approved = False
    db.commit()
    db.refresh(business)
    return business


@router.patch("/businesses/{business_id}/commission")
def set_commission(business_id: uuid.UUID, rate: float, db: Session = Depends(get_db)):
    if not (0 <= rate <= 1):
        raise HTTPException(400, "Rate must be between 0 and 1")
    business = db.get(BusinessProfile, business_id)
    if not business:
        raise HTTPException(404, "Business not found")
    business.commission_rate = rate
    db.commit()
    return {"business_id": business_id, "commission_rate": rate}


@router.get("/kyc/pending", response_model=list[DocumentOut])
def pending_kyc_documents(db: Session = Depends(get_db)):
    return db.query(BusinessDocument).filter(BusinessDocument.status == DocumentStatus.pending).all()


@router.patch("/kyc/{document_id}/approve", response_model=DocumentOut)
def approve_kyc_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(BusinessDocument, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    doc.status = DocumentStatus.approved
    business = db.get(BusinessProfile, doc.business_id)
    other_pending = db.query(BusinessDocument).filter(
        BusinessDocument.business_id == business.id, BusinessDocument.status != DocumentStatus.approved, BusinessDocument.id != doc.id
    ).count()
    if other_pending == 0:
        business.kyc_status = KycStatus.approved
        business.is_verified = True
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/kyc/{document_id}/reject", response_model=DocumentOut)
def reject_kyc_document(document_id: uuid.UUID, reason: str, db: Session = Depends(get_db)):
    doc = db.get(BusinessDocument, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    doc.status = DocumentStatus.rejected
    doc.rejection_reason = reason
    business = db.get(BusinessProfile, doc.business_id)
    business.kyc_status = KycStatus.rejected
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    customers = db.query(User).filter(User.role == "customer").order_by(User.created_at.desc()).all()
    return [
        {"id": c.id, "full_name": c.full_name, "email": c.email, "city": c.city, "created_at": c.created_at, "is_active": c.is_active}
        for c in customers
    ]


@router.patch("/customers/{customer_id}/deactivate")
def deactivate_customer(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    customer = db.get(User, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    customer.is_active = False
    db.commit()
    return {"id": customer_id, "is_active": False}


@router.get("/support-tickets", response_model=list[SupportTicketOut])
def list_support_tickets(status_filter: str | None = None, db: Session = Depends(get_db)):
    query = db.query(SupportTicket)
    if status_filter:
        query = query.filter(SupportTicket.status == status_filter)
    return query.order_by(SupportTicket.created_at.desc()).all()


@router.patch("/support-tickets/{ticket_id}/status", response_model=SupportTicketOut)
def update_ticket_status(ticket_id: uuid.UUID, new_status: str, db: Session = Depends(get_db)):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    return ticket


# --- CMS ---
@router.get("/cms", response_model=list[CmsPageOut])
def list_cms_pages(db: Session = Depends(get_db)):
    return db.query(CmsPage).all()


@router.post("/cms", response_model=CmsPageOut, status_code=201)
def create_cms_page(payload: CmsPageCreate, db: Session = Depends(get_db)):
    if db.query(CmsPage).filter(CmsPage.slug == payload.slug).first():
        raise HTTPException(400, "Slug already exists")
    page = CmsPage(**payload.model_dump())
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@router.put("/cms/{page_id}", response_model=CmsPageOut)
def update_cms_page(page_id: uuid.UUID, payload: CmsPageCreate, db: Session = Depends(get_db)):
    page = db.get(CmsPage, page_id)
    if not page:
        raise HTTPException(404, "Page not found")
    for field, value in payload.model_dump().items():
        setattr(page, field, value)
    db.commit()
    db.refresh(page)
    return page

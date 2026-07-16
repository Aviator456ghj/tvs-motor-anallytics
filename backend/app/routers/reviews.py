import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_business, require_customer
from app.models.booking import Booking
from app.models.business import BusinessProfile
from app.models.enums import BookingStatus
from app.models.engagement import Review
from app.models.user import User
from app.schemas.booking import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _looks_fake(comment: str | None, rating: int) -> bool:
    """Lightweight heuristic placeholder for the AI fake-review-detection service.

    Swap for a real model call (spam/sentiment classifier) later; keeping the
    signature the same lets the AI Service own this without touching callers.
    """
    if not comment:
        return False
    spammy_terms = ("http://", "https://", "www.", "buy now", "click here")
    return any(term in comment.lower() for term in spammy_terms)


@router.post("", response_model=ReviewOut, status_code=201)
def create_review(payload: ReviewCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    booking = db.get(Booking, payload.booking_id)
    if not booking or booking.customer_id != user.id:
        raise HTTPException(404, "Booking not found")
    if booking.status != BookingStatus.completed:
        raise HTTPException(400, "You can only review completed bookings")
    if booking.review:
        raise HTTPException(400, "Booking already reviewed")
    if not (1 <= payload.rating <= 5):
        raise HTTPException(400, "Rating must be between 1 and 5")

    review = Review(
        booking_id=booking.id,
        customer_id=user.id,
        business_id=booking.business_id,
        rating=payload.rating,
        comment=payload.comment,
        is_flagged=_looks_fake(payload.comment, payload.rating),
    )
    db.add(review)

    business = db.get(BusinessProfile, booking.business_id)
    total_score = business.rating_avg * business.rating_count + payload.rating
    business.rating_count += 1
    business.rating_avg = round(total_score / business.rating_count, 2)

    db.commit()
    db.refresh(review)
    return review


@router.get("/business/{business_id}", response_model=list[ReviewOut])
def list_business_reviews(business_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(Review)
        .filter(Review.business_id == business_id, Review.is_flagged.is_(False))
        .order_by(Review.created_at.desc())
        .all()
    )


@router.post("/{review_id}/respond", response_model=ReviewOut)
def respond_to_review(review_id: uuid.UUID, response: str, user: User = Depends(require_business), db: Session = Depends(get_db)):
    review = db.get(Review, review_id)
    business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
    if not review or not business or review.business_id != business.id:
        raise HTTPException(404, "Review not found")
    review.provider_response = response
    db.commit()
    db.refresh(review)
    return review

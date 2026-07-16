import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.engagement import Coupon
from app.schemas.engagement import CouponCreate, CouponOut

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.get("", response_model=list[CouponOut])
def list_coupons(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Coupon).order_by(Coupon.valid_from.desc()).all()


@router.post("", response_model=CouponOut, status_code=201)
def create_coupon(payload: CouponCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(Coupon).filter(Coupon.code == payload.code).first():
        raise HTTPException(400, "Coupon code already exists")
    coupon = Coupon(**payload.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.patch("/{coupon_id}/deactivate", response_model=CouponOut)
def deactivate_coupon(coupon_id: uuid.UUID, db: Session = Depends(get_db), _=Depends(require_admin)):
    coupon = db.get(Coupon, coupon_id)
    if not coupon:
        raise HTTPException(404, "Coupon not found")
    coupon.is_active = False
    db.commit()
    db.refresh(coupon)
    return coupon


@router.get("/validate/{code}", response_model=CouponOut)
def validate_coupon(code: str, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.code == code, Coupon.is_active.is_(True)).first()
    if not coupon:
        raise HTTPException(404, "Invalid or inactive coupon")
    return coupon

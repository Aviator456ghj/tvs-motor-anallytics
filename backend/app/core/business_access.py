"""Shared business-ownership/permission resolution.

A BusinessProfile is reachable by its owner (implicit, full access) or by
any BusinessStaff row granting a permission tier. Every router that acts on
"my business" should depend on `require_business_access(min_role)` instead
of re-deriving ownership itself, so the staff-accounts feature applies
uniformly everywhere.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.business import BusinessProfile, BusinessStaff
from app.models.enums import BusinessStaffRole, UserRole
from app.models.user import User

_ROLE_RANK = {
    BusinessStaffRole.staff: 0,
    BusinessStaffRole.manager: 1,
    BusinessStaffRole.owner: 2,
}


def resolve_business_and_role(user: User, db: Session) -> tuple[BusinessProfile | None, BusinessStaffRole | None]:
    business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
    if business:
        return business, BusinessStaffRole.owner
    staff = db.query(BusinessStaff).filter(BusinessStaff.user_id == user.id).first()
    if staff:
        return db.get(BusinessProfile, staff.business_id), staff.role
    return None, None


def require_business_access(min_role: BusinessStaffRole = BusinessStaffRole.staff):
    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BusinessProfile:
        if user.role != UserRole.business:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Business account required")
        business, role = resolve_business_and_role(user, db)
        if not business:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Business profile not found for this account")
        if _ROLE_RANK[role] < _ROLE_RANK[min_role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"This area requires {min_role.value} access or higher")
        return business

    return dependency

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.business import BusinessProfile
from app.models.catalog import Category

router = APIRouter(prefix="/search", tags=["search"])

# NOTE: naive ILIKE search against Postgres for now. Swap the query building
# below for an Elasticsearch/OpenSearch client once catalog size warrants it —
# the response shape is designed to stay stable across that migration.


@router.get("")
def unified_search(q: str, limit: int = 10, db: Session = Depends(get_db)):
    categories = (
        db.query(Category)
        .filter(Category.is_active.is_(True), Category.name.ilike(f"%{q}%"))
        .limit(limit)
        .all()
    )
    businesses = (
        db.query(BusinessProfile)
        .filter(
            BusinessProfile.is_approved.is_(True),
            or_(BusinessProfile.company_name.ilike(f"%{q}%"), BusinessProfile.city.ilike(f"%{q}%")),
        )
        .order_by(BusinessProfile.rating_avg.desc())
        .limit(limit)
        .all()
    )
    return {
        "categories": [{"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon} for c in categories],
        "businesses": [
            {"id": b.id, "slug": b.slug, "company_name": b.company_name, "city": b.city, "rating_avg": b.rating_avg}
            for b in businesses
        ],
    }

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.catalog import Category
from app.schemas.catalog import CategoryCreate, CategoryOut, CategoryTreeOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(parent_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    query = db.query(Category).filter(Category.is_active.is_(True))
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    return query.order_by(Category.sort_order, Category.name).all()


@router.get("/tree", response_model=list[CategoryTreeOut])
def category_tree(db: Session = Depends(get_db)):
    all_categories = db.query(Category).filter(Category.is_active.is_(True)).order_by(Category.sort_order, Category.name).all()
    by_id = {c.id: CategoryTreeOut(**CategoryOut.model_validate(c).model_dump(), children=[]) for c in all_categories}
    roots: list[CategoryTreeOut] = []
    for c in all_categories:
        node = by_id[c.id]
        if c.parent_id and c.parent_id in by_id:
            by_id[c.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


@router.get("/{slug}", response_model=CategoryOut)
def get_category(slug: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(404, "Category not found")
    return category


@router.post("", response_model=CategoryOut, dependencies=[Depends(require_admin)])
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.slug == payload.slug).first():
        raise HTTPException(400, "Slug already exists")
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(404, "Category not found")
    category.is_active = False
    db.commit()

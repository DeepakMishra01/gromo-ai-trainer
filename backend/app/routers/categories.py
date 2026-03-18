import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.category import Category

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    gromo_category_id: Optional[str]
    is_excluded: bool
    synced_at: Optional[datetime]
    created_at: datetime
    product_count: int = 0

    class Config:
        from_attributes = True


@router.get("", response_model=List[CategoryOut])
def list_categories(include_excluded: bool = False, db: Session = Depends(get_db)):
    query = db.query(Category)
    if not include_excluded:
        query = query.filter(Category.is_excluded == False)  # noqa: E712
    categories = query.order_by(Category.name).all()
    result = []
    for cat in categories:
        out = CategoryOut.model_validate(cat)
        out.product_count = len(cat.products)
        result.append(out)
    return result


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    out = CategoryOut.model_validate(cat)
    out.product_count = len(cat.products)
    return out

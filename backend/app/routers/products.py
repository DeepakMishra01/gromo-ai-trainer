import uuid
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.product import Product
from app.models.category import Category

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str = ""
    name: str
    gromo_product_id: Optional[str]
    payout: Optional[str] = None
    sub_type: Optional[str] = None
    benefits_text: Optional[str] = None
    how_works_text: Optional[str] = None
    terms_conditions_text: Optional[str] = None
    description: Optional[str] = None
    features: Optional[Any] = None
    eligibility: Optional[Any] = None
    fees: Optional[Any] = None
    benefits: Optional[Any] = None
    faqs: Optional[Any] = None
    synced_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ProductListOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str = ""
    name: str
    payout: Optional[str] = None
    sub_type: Optional[str] = None
    description: Optional[str]
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("", response_model=List[ProductListOut])
def list_products(
    category_id: Optional[uuid.UUID] = None,
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Product)
        .join(Category)
        .filter(Category.is_excluded == False)  # noqa: E712
        .options(joinedload(Product.category))
    )
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    products = query.order_by(Product.name).all()
    result = []
    for p in products:
        out = ProductListOut.model_validate(p)
        out.category_name = p.category.name if p.category else ""
        result.append(out)
    return result


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    out = ProductOut.model_validate(product)
    out.category_name = product.category.name if product.category else ""
    return out

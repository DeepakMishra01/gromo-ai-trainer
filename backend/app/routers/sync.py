from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.services.gromo_sync import run_sync
from app.auth import require_admin

router = APIRouter(prefix="/api/sync", tags=["sync"], dependencies=[Depends(require_admin)])


class SyncResponse(BaseModel):
    status: str
    source: str = ""
    categories_synced: int = 0
    products_synced: int = 0
    categories_excluded: int = 0
    products_excluded: int = 0
    message: str = ""


@router.post("", response_model=SyncResponse)
async def trigger_sync(
    demo: bool = Query(False, description="Use demo data instead of live API"),
    db: Session = Depends(get_db),
):
    """Trigger a manual sync from GroMo API (or demo data)."""
    result = await run_sync(db, use_demo=demo)
    return SyncResponse(**result)

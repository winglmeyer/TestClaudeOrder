from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/summary", response_model=schemas.SalesSummary)
def sales_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    return crud.get_sales_summary(db, date_from=date_from, date_to=date_to)


@router.get("/by-day", response_model=list[schemas.SalesByDay])
def sales_by_day(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    return crud.get_sales_by_day(db, date_from=date_from, date_to=date_to)


@router.get("/top-products", response_model=list[schemas.TopProduct])
def top_products(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    return crud.get_top_products(db, date_from=date_from, date_to=date_to, limit=limit)

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..excel_utils import parse_orders_excel

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=schemas.Order, status_code=201)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    return crud.create_order(db, order)


@router.get("", response_model=list[schemas.Order])
def search_orders(
    order_id: int | None = None,
    product_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return crud.search_orders(
        db,
        order_id=order_id,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.get("/{order_id}", response_model=schemas.Order)
def get_order(order_id: int, db: Session = Depends(get_db)):
    db_order = crud.get_order(db, order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@router.put("/{order_id}", response_model=schemas.Order)
def update_order(order_id: int, order: schemas.OrderUpdate, db: Session = Depends(get_db)):
    db_order = crud.update_order(db, order_id, order)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    if not crud.delete_order(db, order_id):
        raise HTTPException(status_code=404, detail="Order not found")


@router.post("/import", response_model=schemas.ImportResult)
async def import_orders(file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()
    try:
        orders, errors = parse_orders_excel(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if orders:
        crud.bulk_create_orders(db, orders)

    return schemas.ImportResult(inserted=len(orders), failed=len(errors), errors=errors)

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas


def create_order(db: Session, order: schemas.OrderCreate) -> models.Order:
    db_order = models.Order(**order.model_dump())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_order(db: Session, order_id: int) -> models.Order | None:
    return db.query(models.Order).filter(models.Order.OrderID == order_id).first()


def search_orders(
    db: Session,
    order_id: int | None = None,
    product_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[models.Order]:
    query = db.query(models.Order)
    if order_id is not None:
        query = query.filter(models.Order.OrderID == order_id)
    if product_id:
        query = query.filter(models.Order.ProductID.ilike(f"%{product_id}%"))
    if date_from is not None:
        query = query.filter(models.Order.OrderDate >= date_from)
    if date_to is not None:
        query = query.filter(models.Order.OrderDate <= date_to)
    return (
        query.order_by(models.Order.OrderDate.desc(), models.Order.OrderID.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_order(db: Session, order_id: int, order: schemas.OrderUpdate) -> models.Order | None:
    db_order = get_order(db, order_id)
    if db_order is None:
        return None
    for key, value in order.model_dump().items():
        setattr(db_order, key, value)
    db.commit()
    db.refresh(db_order)
    return db_order


def delete_order(db: Session, order_id: int) -> bool:
    db_order = get_order(db, order_id)
    if db_order is None:
        return False
    db.delete(db_order)
    db.commit()
    return True


def bulk_create_orders(db: Session, orders: list[schemas.OrderCreate]) -> list[models.Order]:
    db_orders = [models.Order(**order.model_dump()) for order in orders]
    db.add_all(db_orders)
    db.commit()
    for db_order in db_orders:
        db.refresh(db_order)
    return db_orders


def _date_filtered(db: Session, date_from: date | None, date_to: date | None):
    query = db.query(models.Order)
    if date_from is not None:
        query = query.filter(models.Order.OrderDate >= date_from)
    if date_to is not None:
        query = query.filter(models.Order.OrderDate <= date_to)
    return query


def get_sales_summary(
    db: Session, date_from: date | None = None, date_to: date | None = None
) -> dict:
    row = _date_filtered(db, date_from, date_to).with_entities(
        func.count(models.Order.OrderID),
        func.coalesce(func.sum(models.Order.Qty), 0),
        func.coalesce(func.sum(models.Order.Qty * models.Order.Price), 0.0),
    ).one()
    total_orders, total_qty, total_revenue = row
    avg_order_value = (total_revenue / total_orders) if total_orders else 0.0
    return {
        "total_orders": total_orders,
        "total_qty": total_qty,
        "total_revenue": total_revenue,
        "avg_order_value": avg_order_value,
    }


def get_sales_by_day(
    db: Session, date_from: date | None = None, date_to: date | None = None
) -> list[dict]:
    rows = (
        _date_filtered(db, date_from, date_to)
        .with_entities(
            models.Order.OrderDate,
            func.coalesce(func.sum(models.Order.Qty * models.Order.Price), 0.0),
            func.coalesce(func.sum(models.Order.Qty), 0),
            func.count(models.Order.OrderID),
        )
        .group_by(models.Order.OrderDate)
        .order_by(models.Order.OrderDate)
        .all()
    )
    return [
        {"order_date": order_date, "revenue": revenue, "qty": qty, "order_count": order_count}
        for order_date, revenue, qty, order_count in rows
    ]


def get_top_products(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 10,
) -> list[dict]:
    rows = (
        _date_filtered(db, date_from, date_to)
        .with_entities(
            models.Order.ProductID,
            func.coalesce(func.sum(models.Order.Qty), 0),
            func.coalesce(func.sum(models.Order.Qty * models.Order.Price), 0.0),
        )
        .group_by(models.Order.ProductID)
        .order_by(func.sum(models.Order.Qty * models.Order.Price).desc())
        .limit(limit)
        .all()
    )
    return [
        {"product_id": product_id, "qty": qty, "revenue": revenue}
        for product_id, qty, revenue in rows
    ]

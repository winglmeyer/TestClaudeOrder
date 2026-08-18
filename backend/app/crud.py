from datetime import date

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

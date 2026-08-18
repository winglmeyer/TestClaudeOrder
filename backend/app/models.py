from sqlalchemy import Column, Date, Float, Integer, String

from .database import Base


class Order(Base):
    __tablename__ = "orders"

    OrderID = Column(Integer, primary_key=True, autoincrement=True)
    ProductID = Column(String, nullable=False, index=True)
    Qty = Column(Integer, nullable=False)
    Price = Column(Float, nullable=False)
    OrderDate = Column(Date, nullable=False, index=True)

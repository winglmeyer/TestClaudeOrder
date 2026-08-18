from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class OrderBase(BaseModel):
    ProductID: str = Field(..., min_length=1)
    Qty: int = Field(..., gt=0)
    Price: float = Field(..., ge=0)
    OrderDate: date


class OrderCreate(OrderBase):
    pass


class OrderUpdate(OrderBase):
    pass


class Order(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    OrderID: int


class ImportResult(BaseModel):
    inserted: int
    failed: int
    errors: list[str]

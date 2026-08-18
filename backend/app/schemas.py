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
    order_ids: list[int] = []


class SalesSummary(BaseModel):
    total_orders: int
    total_qty: int
    total_revenue: float
    avg_order_value: float


class SalesByDay(BaseModel):
    order_date: date
    revenue: float
    qty: int
    order_count: int


class TopProduct(BaseModel):
    product_id: str
    qty: int
    revenue: float

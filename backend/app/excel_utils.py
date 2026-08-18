from datetime import date, datetime
from io import BytesIO

import pandas as pd
from pydantic import ValidationError

from . import schemas

REQUIRED_COLUMNS = ["OrderID", "ProductID", "Qty", "Price", "OrderDate"]


def parse_orders_excel(content: bytes) -> tuple[list[schemas.OrderCreate], list[str]]:
    """Parse an uploaded Excel file into validated OrderCreate rows.

    Returns (orders, errors). OrderID from the file is ignored since the
    database assigns its own primary key on insert.
    """
    df = pd.read_excel(BytesIO(content))
    df.columns = [str(c).strip() for c in df.columns]

    column_map = {c.lower(): c for c in df.columns}
    missing = [c for c in REQUIRED_COLUMNS if c.lower() not in column_map]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    orders: list[schemas.OrderCreate] = []
    errors: list[str] = []

    for idx, row in df.iterrows():
        excel_row_num = idx + 2  # account for header row and 0-index
        try:
            order_date_raw = row[column_map["orderdate"]]
            if isinstance(order_date_raw, (date, datetime)):
                order_date = order_date_raw
            else:
                order_date = pd.to_datetime(order_date_raw).date()

            order = schemas.OrderCreate(
                ProductID=str(row[column_map["productid"]]).strip(),
                Qty=int(row[column_map["qty"]]),
                Price=float(row[column_map["price"]]),
                OrderDate=order_date,
            )
            orders.append(order)
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append(f"Row {excel_row_num}: {exc}")

    return orders, errors

from datetime import date
from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_order(product_id="P1", qty=2, price=9.99, order_date="2026-08-01"):
    return {
        "ProductID": product_id,
        "Qty": qty,
        "Price": price,
        "OrderDate": order_date,
    }


def test_create_and_get_order(client):
    response = client.post("/api/orders", json=make_order())
    assert response.status_code == 201
    body = response.json()
    assert body["ProductID"] == "P1"
    assert "OrderID" in body

    order_id = body["OrderID"]
    response = client.get(f"/api/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["OrderID"] == order_id


def test_get_missing_order_returns_404(client):
    response = client.get("/api/orders/999")
    assert response.status_code == 404


def test_search_orders_by_product_and_date(client):
    client.post("/api/orders", json=make_order(product_id="ABC", order_date="2026-01-10"))
    client.post("/api/orders", json=make_order(product_id="XYZ", order_date="2026-02-15"))

    response = client.get("/api/orders", params={"product_id": "abc"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["ProductID"] == "ABC"

    response = client.get(
        "/api/orders", params={"date_from": "2026-02-01", "date_to": "2026-02-28"}
    )
    results = response.json()
    assert len(results) == 1
    assert results[0]["ProductID"] == "XYZ"


def test_update_and_delete_order(client):
    order_id = client.post("/api/orders", json=make_order()).json()["OrderID"]

    updated = make_order(qty=5)
    response = client.put(f"/api/orders/{order_id}", json=updated)
    assert response.status_code == 200
    assert response.json()["Qty"] == 5

    response = client.delete(f"/api/orders/{order_id}")
    assert response.status_code == 204

    response = client.get(f"/api/orders/{order_id}")
    assert response.status_code == 404


def test_import_orders_from_excel(client):
    df = pd.DataFrame(
        [
            {
                "OrderID": 1,
                "ProductID": "P100",
                "Qty": 3,
                "Price": 12.5,
                "OrderDate": date(2026, 3, 1),
            },
            {
                "OrderID": 2,
                "ProductID": "P200",
                "Qty": "not-a-number",
                "Price": 5,
                "OrderDate": date(2026, 3, 2),
            },
        ]
    )
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    response = client.post(
        "/api/orders/import",
        files={
            "file": (
                "orders.xlsx",
                buffer,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["inserted"] == 1
    assert body["failed"] == 1
    assert len(body["errors"]) == 1

    response = client.get("/api/orders", params={"product_id": "P100"})
    assert len(response.json()) == 1

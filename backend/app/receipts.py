"""Generate a printable PDF receipt and a plain-text summary for orders."""

from __future__ import annotations

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from . import models

COMPANY_NAME = "Order Enquiry System"

_NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def _line_total(order: models.Order) -> float:
    return order.Qty * order.Price


def generate_receipt_pdf(order: models.Order) -> bytes:
    """Build a one-page PDF receipt for a single order."""
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, COMPANY_NAME, **_NEXT_LINE)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Order Receipt", **_NEXT_LINE)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Order ID: {order.OrderID}", **_NEXT_LINE)
    pdf.cell(0, 6, f"Order Date: {order.OrderDate.isoformat()}", **_NEXT_LINE)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(60, 8, "Product ID", border=1)
    pdf.cell(30, 8, "Qty", border=1)
    pdf.cell(40, 8, "Price", border=1)
    pdf.cell(40, 8, "Line Total", border=1, **_NEXT_LINE)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 8, str(order.ProductID), border=1)
    pdf.cell(30, 8, str(order.Qty), border=1)
    pdf.cell(40, 8, f"{order.Price:.2f}", border=1)
    pdf.cell(40, 8, f"{_line_total(order):.2f}", border=1, **_NEXT_LINE)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, f"Total: {_line_total(order):.2f}", **_NEXT_LINE)

    return bytes(pdf.output())

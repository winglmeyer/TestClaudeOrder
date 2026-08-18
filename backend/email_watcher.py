"""Poll an IMAP mailbox for "Order Enquiry" emails and import their Excel attachments.

Looks for unread emails whose subject contains SUBJECT_FILTER, extracts the
first .xlsx/.xls attachment from each, and POSTs it to the running Order
Enquiry API's /api/orders/import endpoint. An email is only marked as read
after its attachment has been successfully imported, so failures are retried
on the next poll.

Configuration is read from environment variables (see .env.example):
  IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD, IMAP_FOLDER,
  SUBJECT_FILTER, API_BASE_URL, POLL_INTERVAL_SECONDS

Usage:
  python email_watcher.py          # polls forever
  python email_watcher.py --once   # single pass, e.g. for cron/Task Scheduler
"""

import email
import imaplib
import os
import sys
import time
from email.header import decode_header
from email.message import EmailMessage, Message
from email.utils import parseaddr

import requests

IMAP_HOST = os.environ["IMAP_HOST"]
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USER = os.environ["IMAP_USER"]
IMAP_PASSWORD = os.environ["IMAP_PASSWORD"]
IMAP_FOLDER = os.environ.get("IMAP_FOLDER", "INBOX")
DRAFTS_FOLDER = os.environ.get("IMAP_DRAFTS_FOLDER", "[Gmail]/Drafts")
SUBJECT_FILTER = os.environ.get("SUBJECT_FILTER", "Order Enquiry")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Order Enquiry System")

EXCEL_EXTENSIONS = (".xlsx", ".xls")


def decode_subject(raw_subject: str) -> str:
    parts = decode_header(raw_subject)
    decoded = ""
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded += text.decode(charset or "utf-8", errors="replace")
        else:
            decoded += text
    return decoded


def find_excel_attachment(msg: Message) -> tuple[str, bytes] | None:
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        decoded_name = decode_subject(filename)
        if decoded_name.lower().endswith(EXCEL_EXTENSIONS):
            payload = part.get_payload(decode=True)
            if payload:
                return decoded_name, payload
    return None


def import_attachment(filename: str, content: bytes) -> dict | None:
    content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if filename.lower().endswith(".xlsx")
        else "application/vnd.ms-excel"
    )
    response = requests.post(
        f"{API_BASE_URL}/api/orders/import",
        files={"file": (filename, content, content_type)},
        timeout=30,
    )
    if response.status_code != 200:
        print(f"  Import failed ({response.status_code}): {response.text}")
        return None

    result = response.json()
    print(f"  Imported {result['inserted']} row(s), {result['failed']} failed")
    for err in result.get("errors", []):
        print(f"    {err}")
    return result


def build_receipt_text(order_ids: list[int]) -> str:
    """Fetch each imported order back from the API and format a plain-text receipt."""
    lines = [COMPANY_NAME, "Order Receipt", "", f"{len(order_ids)} order(s) received:", ""]
    lines.append(
        f"{'OrderID':<10}{'ProductID':<15}{'Qty':<8}{'Price':<10}{'Line Total':<12}{'Date'}"
    )
    total = 0.0
    for order_id in order_ids:
        response = requests.get(f"{API_BASE_URL}/api/orders/{order_id}", timeout=30)
        if response.status_code != 200:
            continue
        order = response.json()
        line_total = order["Qty"] * order["Price"]
        total += line_total
        lines.append(
            f"{order['OrderID']:<10}{order['ProductID']:<15}{order['Qty']:<8}"
            f"{order['Price']:<10.2f}{line_total:<12.2f}{order['OrderDate']}"
        )
    lines.append("")
    lines.append(f"Total: {total:.2f}")
    return "\n".join(lines)


def create_draft_reply(conn: imaplib.IMAP4_SSL, to_addr: str, subject: str, body: str) -> None:
    """Save a reply as a draft in the Gmail Drafts folder (not sent automatically)."""
    if not to_addr:
        print("  No sender address found; skipping draft.")
        return

    msg = EmailMessage()
    msg["From"] = IMAP_USER
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    status, _ = conn.append(
        DRAFTS_FOLDER, "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes()
    )
    if status == "OK":
        print(f"  Draft reply saved to {DRAFTS_FOLDER} for {to_addr}.")
    else:
        print(f"  Failed to save draft reply: {status}")


def process_mailbox() -> None:
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        conn.login(IMAP_USER, IMAP_PASSWORD)
        conn.select(IMAP_FOLDER)

        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            print(f"IMAP search failed: {status}")
            return

        message_ids = data[0].split()
        if not message_ids:
            print("No new emails.")
            return

        for msg_id in message_ids:
            status, msg_data = conn.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = decode_subject(msg.get("Subject", ""))

            if SUBJECT_FILTER.lower() not in subject.lower():
                continue

            print(f"Processing email: {subject!r}")
            attachment = find_excel_attachment(msg)
            if attachment is None:
                print("  No Excel attachment found; leaving unread.")
                continue

            filename, content = attachment
            print(f"  Found attachment: {filename}")
            result = import_attachment(filename, content)
            if result is not None:
                conn.store(msg_id, "+FLAGS", "\\Seen")
                order_ids = result.get("order_ids", [])
                if order_ids:
                    _, sender_addr = parseaddr(msg.get("From", ""))
                    receipt_text = build_receipt_text(order_ids)
                    create_draft_reply(
                        conn,
                        to_addr=sender_addr,
                        subject=f"Re: {subject} - Receipt",
                        body=receipt_text,
                    )
    finally:
        try:
            conn.close()
        except imaplib.IMAP4.error:
            pass
        conn.logout()


def main() -> None:
    run_once = "--once" in sys.argv

    while True:
        try:
            process_mailbox()
        except Exception as exc:  # noqa: BLE001 - keep polling despite transient errors
            print(f"Error while processing mailbox: {exc}")

        if run_once:
            break
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

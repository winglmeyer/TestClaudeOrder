"""Poll Gmail for "Order Enquiry" emails and import their Excel attachments.

Looks for unread emails whose subject contains SUBJECT_FILTER, extracts the
first .xlsx/.xls attachment from each, and POSTs it to the running Order
Enquiry API's /api/orders/import endpoint. An email is only marked as read
after its attachment has been successfully imported, so failures are retried
on the next poll.

Uses the Gmail API (OAuth2), not IMAP. Run gmail_auth_setup.py once first to
obtain a refresh token.

Configuration is read from environment variables (see .env.example):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN,
  SUBJECT_FILTER, API_BASE_URL, POLL_INTERVAL_SECONDS, COMPANY_NAME

Usage:
  python email_watcher.py          # polls forever
  python email_watcher.py --once   # single pass, e.g. for cron/Task Scheduler
"""

import base64
import os
import sys
import time
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]
SUBJECT_FILTER = os.environ.get("SUBJECT_FILTER", "Order Enquiry")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Order Enquiry System")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]
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


def get_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_header(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def find_excel_attachment(service, msg_id: str, payload: dict) -> tuple[str, bytes] | None:
    stack = list(payload.get("parts") or [])
    while stack:
        part = stack.pop()
        sub_parts = part.get("parts")
        if sub_parts:
            stack.extend(sub_parts)
            continue

        filename = decode_subject(part.get("filename") or "")
        if not filename.lower().endswith(EXCEL_EXTENSIONS):
            continue

        body = part.get("body", {})
        data = body.get("data")
        if data is None and body.get("attachmentId"):
            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=msg_id, id=body["attachmentId"])
                .execute()
            )
            data = attachment.get("data")
        if data:
            padded = data + "=" * (-len(data) % 4)
            return filename, base64.urlsafe_b64decode(padded)
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


def create_draft_reply(
    service, thread_id: str, to_addr: str, subject: str, body: str, in_reply_to: str
) -> None:
    """Save a reply as a Gmail draft (not sent automatically)."""
    if not to_addr:
        print("  No sender address found; skipping draft.")
        return

    msg = EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        service.users().drafts().create(
            userId="me", body={"message": {"raw": raw, "threadId": thread_id}}
        ).execute()
        print(f"  Draft reply saved for {to_addr}.")
    except HttpError as exc:
        print(f"  Failed to save draft reply: {exc}")


def process_mailbox(service) -> None:
    query = f'is:unread subject:"{SUBJECT_FILTER}"'
    response = service.users().messages().list(userId="me", q=query).execute()
    messages = response.get("messages", [])
    if not messages:
        print("No new emails.")
        return

    for meta in messages:
        msg_id = meta["id"]
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = msg["payload"].get("headers", [])
        subject = decode_subject(get_header(headers, "Subject"))

        if SUBJECT_FILTER.lower() not in subject.lower():
            continue

        print(f"Processing email: {subject!r}")
        attachment = find_excel_attachment(service, msg_id, msg["payload"])
        if attachment is None:
            print("  No Excel attachment found; leaving unread.")
            continue

        filename, content = attachment
        print(f"  Found attachment: {filename}")
        result = import_attachment(filename, content)
        if result is None:
            continue

        service.users().messages().modify(
            userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()

        order_ids = result.get("order_ids", [])
        if not order_ids:
            continue

        _, sender_addr = parseaddr(get_header(headers, "From"))
        receipt_text = build_receipt_text(order_ids)
        create_draft_reply(
            service,
            thread_id=msg["threadId"],
            to_addr=sender_addr,
            subject=f"Re: {subject} - Receipt",
            body=receipt_text,
            in_reply_to=get_header(headers, "Message-ID"),
        )


def main() -> None:
    run_once = "--once" in sys.argv
    service = get_gmail_service()

    while True:
        try:
            process_mailbox(service)
        except HttpError as exc:
            print(f"Gmail API error: {exc}")
        except Exception as exc:  # noqa: BLE001 - keep polling despite transient errors
            print(f"Error while processing mailbox: {exc}")

        if run_once:
            break
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

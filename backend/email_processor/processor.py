"""Email fetching and processing using the Gmail API."""

from __future__ import annotations

import base64
import email.utils
import re
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from backend.models.schemas import EmailMessage


def _get_gmail_service(credentials: Credentials) -> Any:
    """Build and return a Gmail API service object."""
    return build("gmail", "v1", credentials=credentials)


def _decode_body(payload: dict[str, Any]) -> str:
    """Recursively extract and decode the text body from a Gmail message payload."""
    body = ""

    if payload.get("mimeType", "").startswith("text/plain"):
        data = payload.get("body", {}).get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        part_body = _decode_body(part)
        if part_body:
            body += part_body

    return body


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    """Get a specific header value from a list of Gmail headers."""
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _clean_email_body(body: str) -> str:
    """Clean up email body text by removing excessive whitespace and signatures."""
    # Remove URLs
    body = re.sub(r"https?://\S+", "[link]", body)
    # Collapse multiple newlines
    body = re.sub(r"\n{3,}", "\n\n", body)
    # Collapse multiple spaces
    body = re.sub(r" {2,}", " ", body)
    # Truncate very long emails
    if len(body) > 2000:
        body = body[:2000] + "..."
    return body.strip()


def fetch_emails(
    credentials: Credentials,
    max_results: int = 500,
) -> list[EmailMessage]:
    """Fetch emails from the user's Gmail account.

    Retrieves both sent and received emails to build a complete picture
    of the user's communication style and interests.

    Args:
        credentials: Google OAuth2 credentials.
        max_results: Maximum number of emails to fetch.

    Returns:
        A list of EmailMessage objects.
    """
    service = _get_gmail_service(credentials)
    messages: list[EmailMessage] = []

    # Fetch from both inbox and sent mail
    for query in ["in:inbox", "in:sent"]:
        page_token = None
        fetched = 0
        per_query_limit = max_results // 2

        while fetched < per_query_limit:
            batch_size = min(100, per_query_limit - fetched)
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=batch_size,
                    pageToken=page_token,
                )
                .execute()
            )

            message_refs = results.get("messages", [])
            if not message_refs:
                break

            for ref in message_refs:
                msg_data = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=ref["id"],
                        format="full",
                    )
                    .execute()
                )

                payload = msg_data.get("payload", {})
                headers = payload.get("headers", [])

                body = _decode_body(payload)
                body = _clean_email_body(body)

                msg = EmailMessage(
                    message_id=msg_data["id"],
                    subject=_get_header(headers, "Subject"),
                    sender=_get_header(headers, "From"),
                    recipient=_get_header(headers, "To"),
                    date=_get_header(headers, "Date"),
                    body=body,
                    snippet=msg_data.get("snippet", ""),
                )
                messages.append(msg)
                fetched += 1

            page_token = results.get("nextPageToken")
            if not page_token:
                break

    return messages


def get_user_email(credentials: Credentials) -> str:
    """Get the authenticated user's email address.

    Args:
        credentials: Google OAuth2 credentials.

    Returns:
        The user's email address.
    """
    service = _get_gmail_service(credentials)
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def categorize_emails(
    emails: list[EmailMessage],
    user_email: str,
) -> dict[str, list[EmailMessage]]:
    """Categorize emails into sent and received.

    Args:
        emails: List of email messages.
        user_email: The authenticated user's email address.

    Returns:
        Dictionary with 'sent' and 'received' keys.
    """
    sent: list[EmailMessage] = []
    received: list[EmailMessage] = []

    for msg in emails:
        sender_email = email.utils.parseaddr(msg.sender)[1].lower()
        if sender_email == user_email.lower():
            sent.append(msg)
        else:
            received.append(msg)

    return {"sent": sent, "received": received}

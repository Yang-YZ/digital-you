"""IMAP email fetching utilities.

Connects to a user-supplied IMAP server with a username and password
(typically an app password), then pulls down a sample of recent
messages from selected mailboxes for persona analysis.
"""
from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import Message
from typing import Iterable

from bs4 import BeautifulSoup


@dataclass
class EmailRecord:
    mailbox: str
    uid: str
    date: str
    sender: str
    to: str
    subject: str
    body: str

    def to_compact_dict(self) -> dict:
        return {
            "mailbox": self.mailbox,
            "date": self.date,
            "from": self.sender,
            "to": self.to,
            "subject": self.subject,
            "body": self.body[:2000],
        }


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_body(msg: Message) -> str:
    """Pull a reasonable plain-text body out of an email message."""
    text_parts: list[str] = []
    html_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp.lower():
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="replace")
            except LookupError:
                decoded = payload.decode("utf-8", errors="replace")
            if ctype == "text/plain":
                text_parts.append(decoded)
            elif ctype == "text/html":
                html_parts.append(decoded)
    else:
        payload = msg.get_payload(decode=True)
        if payload is not None:
            charset = msg.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="replace")
            except LookupError:
                decoded = payload.decode("utf-8", errors="replace")
            if msg.get_content_type() == "text/html":
                html_parts.append(decoded)
            else:
                text_parts.append(decoded)

    body = "\n".join(text_parts).strip()
    if not body and html_parts:
        soup = BeautifulSoup("\n".join(html_parts), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        body = soup.get_text(separator="\n").strip()

    # Strip quoted replies and signatures heuristically
    body = re.sub(r"\n>+.*", "", body)
    body = re.sub(r"\r", "", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def fetch_emails(
    host: str,
    username: str,
    password: str,
    mailboxes: Iterable[str] = ("INBOX", "Sent"),
    per_mailbox_limit: int = 50,
    port: int = 993,
) -> list[EmailRecord]:
    """Fetch the most recent N emails from each mailbox.

    Returns a list of EmailRecord objects.
    """
    records: list[EmailRecord] = []
    with imaplib.IMAP4_SSL(host, port) as imap:
        imap.login(username, password)
        for raw_mailbox in mailboxes:
            mailbox = raw_mailbox.strip()
            if not mailbox:
                continue
            try:
                status, _ = imap.select(f'"{mailbox}"', readonly=True)
            except imaplib.IMAP4.error:
                continue
            if status != "OK":
                continue

            status, data = imap.uid("search", None, "ALL")
            if status != "OK" or not data or not data[0]:
                continue
            uids = data[0].split()
            uids = uids[-per_mailbox_limit:]

            for uid in uids:
                status, msg_data = imap.uid("fetch", uid, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                if not isinstance(raw, (bytes, bytearray)):
                    continue
                msg = email.message_from_bytes(raw)
                records.append(
                    EmailRecord(
                        mailbox=mailbox,
                        uid=uid.decode(),
                        date=_decode(msg.get("Date")),
                        sender=_decode(msg.get("From")),
                        to=_decode(msg.get("To")),
                        subject=_decode(msg.get("Subject")),
                        body=_extract_body(msg),
                    )
                )
        try:
            imap.logout()
        except Exception:
            pass
    return records

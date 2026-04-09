"""Tests for the email processor module."""

from backend.email_processor.processor import (
    _clean_email_body,
    _decode_body,
    _get_header,
    categorize_emails,
)
from backend.models.schemas import EmailMessage


class TestGetHeader:
    def test_returns_matching_header(self):
        headers = [
            {"name": "Subject", "value": "Hello"},
            {"name": "From", "value": "alice@example.com"},
        ]
        assert _get_header(headers, "Subject") == "Hello"

    def test_case_insensitive(self):
        headers = [{"name": "SUBJECT", "value": "Test"}]
        assert _get_header(headers, "subject") == "Test"

    def test_returns_empty_when_not_found(self):
        headers = [{"name": "From", "value": "alice@example.com"}]
        assert _get_header(headers, "Subject") == ""

    def test_empty_headers(self):
        assert _get_header([], "Subject") == ""


class TestCleanEmailBody:
    def test_removes_urls(self):
        body = "Check this out https://example.com/page and this http://test.org"
        cleaned = _clean_email_body(body)
        assert "https://example.com" not in cleaned
        assert "[link]" in cleaned

    def test_collapses_newlines(self):
        body = "Line 1\n\n\n\n\nLine 2"
        cleaned = _clean_email_body(body)
        assert "\n\n\n" not in cleaned

    def test_collapses_spaces(self):
        body = "Too   many    spaces"
        cleaned = _clean_email_body(body)
        assert "   " not in cleaned

    def test_truncates_long_emails(self):
        body = "A" * 5000
        cleaned = _clean_email_body(body)
        assert len(cleaned) <= 2010  # 2000 + "..."
        assert cleaned.endswith("...")

    def test_strips_whitespace(self):
        body = "  hello  "
        assert _clean_email_body(body) == "hello"


class TestDecodeBody:
    def test_plain_text_body(self):
        import base64

        text = "Hello, World!"
        encoded = base64.urlsafe_b64encode(text.encode()).decode()
        payload = {
            "mimeType": "text/plain",
            "body": {"data": encoded},
        }
        assert _decode_body(payload) == text

    def test_empty_payload(self):
        payload = {"mimeType": "text/html", "body": {}}
        assert _decode_body(payload) == ""

    def test_multipart_payload(self):
        import base64

        text = "Nested content"
        encoded = base64.urlsafe_b64encode(text.encode()).decode()
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": encoded},
                }
            ],
        }
        assert _decode_body(payload) == text


class TestCategorizeEmails:
    def _make_email(self, sender: str, recipient: str) -> EmailMessage:
        return EmailMessage(
            message_id="test",
            subject="Test",
            sender=sender,
            recipient=recipient,
        )

    def test_categorizes_sent_and_received(self):
        emails = [
            self._make_email("me@example.com", "other@example.com"),
            self._make_email("other@example.com", "me@example.com"),
            self._make_email("Me <me@example.com>", "other@example.com"),
        ]
        result = categorize_emails(emails, "me@example.com")
        assert len(result["sent"]) == 2
        assert len(result["received"]) == 1

    def test_empty_list(self):
        result = categorize_emails([], "me@example.com")
        assert len(result["sent"]) == 0
        assert len(result["received"]) == 0

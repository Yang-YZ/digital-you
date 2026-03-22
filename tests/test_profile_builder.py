"""Tests for the profile builder module."""

from backend.models.schemas import EmailMessage
from backend.profile_builder.builder import _prepare_email_summary


class TestPrepareEmailSummary:
    def _make_email(
        self,
        subject: str = "Test",
        body: str = "Hello",
        sender: str = "alice@example.com",
        recipient: str = "bob@example.com",
    ) -> EmailMessage:
        return EmailMessage(
            message_id="test",
            subject=subject,
            sender=sender,
            recipient=recipient,
            body=body,
        )

    def test_basic_summary(self):
        emails = [self._make_email(subject="Hello", body="How are you?")]
        summary = _prepare_email_summary(emails)
        assert "Subject: Hello" in summary
        assert "Body: How are you?" in summary

    def test_uses_snippet_when_no_body(self):
        email = EmailMessage(
            message_id="test",
            subject="No body",
            sender="a@example.com",
            recipient="b@example.com",
            snippet="Short snippet",
        )
        summary = _prepare_email_summary([email])
        assert "Snippet: Short snippet" in summary

    def test_respects_max_chars(self):
        emails = [self._make_email(body="X" * 1000) for _ in range(100)]
        summary = _prepare_email_summary(emails, max_chars=500)
        assert len(summary) <= 600  # Some overhead for headers

    def test_empty_emails(self):
        summary = _prepare_email_summary([])
        assert summary == ""

    def test_multiple_emails_included(self):
        emails = [
            self._make_email(subject="First"),
            self._make_email(subject="Second"),
        ]
        summary = _prepare_email_summary(emails)
        assert "Subject: First" in summary
        assert "Subject: Second" in summary

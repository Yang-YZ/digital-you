"""Shared test fixtures for the Digital You test suite."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app, _sessions
from backend.models.schemas import EmailMessage, UserProfile


@pytest.fixture
def client():
    """Create a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def sample_profile() -> UserProfile:
    """Create a sample UserProfile for testing."""
    return UserProfile(
        email="test@example.com",
        name="Test User",
        personality_traits=["friendly", "curious", "detail-oriented"],
        hobbies=["reading", "hiking", "cooking"],
        interests=["technology", "science", "travel"],
        communication_style="casual and warm",
        frequently_discussed_topics=["AI", "travel", "books"],
        purchase_categories=["books", "electronics", "outdoor gear"],
        writing_tone="friendly and informal",
        summary="A curious tech enthusiast who loves the outdoors and cooking.",
    )


@pytest.fixture
def sample_emails() -> list[EmailMessage]:
    """Create a list of sample emails for testing."""
    return [
        EmailMessage(
            message_id="msg-001",
            subject="Weekend hiking trip",
            sender="Test User <test@example.com>",
            recipient="friend@example.com",
            date="Mon, 1 Jan 2026 10:00:00 -0000",
            body="Hey! Want to go hiking this weekend? I found a great trail.",
        ),
        EmailMessage(
            message_id="msg-002",
            subject="Re: Weekend hiking trip",
            sender="friend@example.com",
            recipient="test@example.com",
            date="Mon, 1 Jan 2026 11:00:00 -0000",
            body="Sounds great! What time works for you?",
        ),
        EmailMessage(
            message_id="msg-003",
            subject="Your order has shipped",
            sender="orders@bookstore.com",
            recipient="test@example.com",
            date="Tue, 2 Jan 2026 09:00:00 -0000",
            body="Your order of 'AI and Machine Learning' has shipped.",
        ),
        EmailMessage(
            message_id="msg-004",
            subject="Project update",
            sender="Test User <test@example.com>",
            recipient="colleague@work.com",
            date="Wed, 3 Jan 2026 14:00:00 -0000",
            body="Hi! Here's the latest update on the project. I've been exploring some new ML approaches.",
        ),
        EmailMessage(
            message_id="msg-005",
            subject="Recipe exchange",
            sender="Test User <test@example.com>",
            recipient="family@example.com",
            date="Thu, 4 Jan 2026 18:00:00 -0000",
            body="Hey, I tried that pasta recipe you sent - it was amazing! Here's my take on it.",
        ),
    ]


@pytest.fixture
def authenticated_session(sample_profile):
    """Create a fake authenticated session with a profile.

    Yields the session_id and cleans up after the test.
    """
    session_id = "test-session-e2e"
    _sessions[session_id] = {
        "credentials": {
            "token": "fake-token",
            "refresh_token": "fake-refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "fake-client-id",
            "client_secret": "fake-client-secret",
            "scopes": [],
        },
        "email": "test@example.com",
        "profile": sample_profile,
    }
    yield session_id
    _sessions.pop(session_id, None)


@pytest.fixture
def unauthenticated_session():
    """Create a session without a profile built yet.

    Yields the session_id and cleans up after the test.
    """
    session_id = "test-session-no-profile"
    _sessions[session_id] = {
        "credentials": {
            "token": "fake-token",
            "refresh_token": "fake-refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "fake-client-id",
            "client_secret": "fake-client-secret",
            "scopes": [],
        },
        "email": "test@example.com",
        "profile": None,
    }
    yield session_id
    _sessions.pop(session_id, None)


def make_mock_openai_response(content: str) -> MagicMock:
    """Create a mock OpenAI chat completion response.

    Args:
        content: The text content to return as the response.

    Returns:
        A MagicMock that mimics openai.chat.completions.create() return value.
    """
    mock_message = MagicMock()
    mock_message.content = content

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    return mock_response

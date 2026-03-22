"""End-to-end tests for the Digital You application.

These tests exercise the complete user flow — from authentication through
profile building to chat and email reply — with external services (Gmail API,
OpenAI API) mocked out so they can run without real credentials.

Run with:
    pytest tests/test_e2e.py -v
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import _sessions, app
from backend.models.schemas import UserProfile
from tests.conftest import make_mock_openai_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_PROFILE_JSON = json.dumps(
    {
        "name": "Test User",
        "personality_traits": ["friendly", "curious"],
        "hobbies": ["reading", "hiking"],
        "interests": ["technology", "science"],
        "communication_style": "casual and warm",
        "frequently_discussed_topics": ["AI", "travel"],
        "purchase_categories": ["books", "electronics"],
        "writing_tone": "friendly and informal",
        "summary": "A curious tech enthusiast who loves the outdoors.",
    }
)


def _build_fake_gmail_service(user_email: str, messages_data: list[dict]):
    """Build a mock Gmail API service that returns pre-configured messages.

    Args:
        user_email: The email address to return from getProfile.
        messages_data: List of dicts, each containing 'id', 'payload',
                       and optionally 'snippet'.
    """
    service = MagicMock()

    # Mock users().getProfile()
    profile_result = MagicMock()
    profile_result.execute.return_value = {"emailAddress": user_email}
    service.users.return_value.getProfile.return_value = profile_result

    # Mock users().messages().list()
    message_refs = [{"id": m["id"]} for m in messages_data]
    list_result = MagicMock()
    list_result.execute.return_value = {
        "messages": message_refs,
    }
    service.users.return_value.messages.return_value.list.return_value = list_result

    # Mock users().messages().get() — returns the right message for each id
    def _get_message(**kwargs):
        msg_id = kwargs.get("id", "")
        for m in messages_data:
            if m["id"] == msg_id:
                result = MagicMock()
                result.execute.return_value = m
                return result
        result = MagicMock()
        result.execute.return_value = messages_data[0] if messages_data else {}
        return result

    service.users.return_value.messages.return_value.get.side_effect = _get_message

    return service


def _make_gmail_message(
    msg_id: str,
    subject: str,
    sender: str,
    recipient: str,
    body_text: str,
    snippet: str = "",
) -> dict:
    """Create a fake Gmail API message payload."""
    import base64

    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    return {
        "id": msg_id,
        "snippet": snippet or body_text[:100],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "To", "value": recipient},
                {"name": "Date", "value": "Mon, 1 Jan 2026 10:00:00 -0000"},
            ],
            "body": {"data": encoded_body},
        },
    }


# ---------------------------------------------------------------------------
# E2E Test: Full User Flow
# ---------------------------------------------------------------------------


class TestEndToEndUserFlow:
    """Test the complete user journey through the application.

    This simulates the full lifecycle:
    1. Login (get auth URL)
    2. OAuth callback (exchange code for session)
    3. Build profile (fetch emails → extract personality)
    4. Retrieve profile
    5. Chat with digital representative
    6. Generate email reply
    """

    def test_full_flow_login_to_chat(self, client, monkeypatch):
        """Test the complete flow from login through profile build to chat."""

        # -- Step 1: Start login flow --
        monkeypatch.setattr(
            "backend.main.get_authorization_url",
            lambda: ("https://accounts.google.com/o/oauth2/auth?state=e2e-state", "e2e-state"),
        )

        resp = client.get("/auth/login")
        assert resp.status_code == 200
        auth_url = resp.json()["auth_url"]
        assert "accounts.google.com" in auth_url

        # -- Step 2: OAuth callback --
        fake_gmail_messages = [
            _make_gmail_message(
                "m1", "Weekend hiking", "Test User <test@example.com>",
                "friend@example.com", "Want to go hiking this weekend?",
            ),
            _make_gmail_message(
                "m2", "Book order shipped", "orders@bookstore.com",
                "test@example.com", "Your order of AI Fundamentals has shipped.",
            ),
        ]
        fake_service = _build_fake_gmail_service("test@example.com", fake_gmail_messages)

        # Mock the OAuth exchange and Gmail service
        mock_credentials = MagicMock()
        mock_credentials.token = "fake-token"
        mock_credentials.refresh_token = "fake-refresh"
        mock_credentials.token_uri = "https://oauth2.googleapis.com/token"
        mock_credentials.client_id = "fake-id"
        mock_credentials.client_secret = "fake-secret"
        mock_credentials.scopes = []

        monkeypatch.setattr(
            "backend.main.exchange_code_for_credentials",
            lambda code: mock_credentials,
        )
        monkeypatch.setattr(
            "backend.main.credentials_to_dict",
            lambda creds: {
                "token": "fake-token",
                "refresh_token": "fake-refresh",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "fake-id",
                "client_secret": "fake-secret",
                "scopes": [],
            },
        )
        monkeypatch.setattr(
            "backend.main.get_user_email",
            lambda creds: "test@example.com",
        )

        resp = client.get("/auth/callback?code=fake-auth-code&state=e2e-state")
        assert resp.status_code == 200
        callback_data = resp.json()
        session_id = callback_data["session_id"]
        assert callback_data["email"] == "test@example.com"
        assert session_id == "e2e-state"

        # -- Step 3: Build profile --
        # Mock Gmail fetch_emails and OpenAI build_profile
        monkeypatch.setattr(
            "backend.main.fetch_emails",
            lambda creds, max_results: [
                # Return EmailMessage objects
                __import__("backend.models.schemas", fromlist=["EmailMessage"]).EmailMessage(
                    message_id="m1",
                    subject="Weekend hiking",
                    sender="Test User <test@example.com>",
                    recipient="friend@example.com",
                    body="Want to go hiking this weekend?",
                ),
                __import__("backend.models.schemas", fromlist=["EmailMessage"]).EmailMessage(
                    message_id="m2",
                    subject="Book order shipped",
                    sender="orders@bookstore.com",
                    recipient="test@example.com",
                    body="Your order of AI Fundamentals has shipped.",
                ),
            ],
        )
        monkeypatch.setattr(
            "backend.main.build_profile",
            lambda emails, user_email: UserProfile(
                email=user_email,
                name="Test User",
                personality_traits=["friendly", "curious"],
                hobbies=["reading", "hiking"],
                interests=["technology", "science"],
                communication_style="casual and warm",
                frequently_discussed_topics=["AI", "travel"],
                purchase_categories=["books", "electronics"],
                writing_tone="friendly and informal",
                summary="A curious tech enthusiast who loves the outdoors.",
            ),
        )

        resp = client.post(
            f"/profile/build?session_id={session_id}",
            json={"max_emails": 100},
        )
        assert resp.status_code == 200
        profile_data = resp.json()
        assert profile_data["email_count"] == 2
        assert profile_data["profile"]["name"] == "Test User"
        assert "friendly" in profile_data["profile"]["personality_traits"]
        assert "hiking" in profile_data["profile"]["hobbies"]

        # -- Step 4: Get profile --
        resp = client.get(f"/profile?session_id={session_id}")
        assert resp.status_code == 200
        assert resp.json()["profile"]["email"] == "test@example.com"

        # -- Step 5: Chat --
        monkeypatch.setattr(
            "backend.main.generate_chat_response",
            lambda profile, message, conversation_history: (
                "Hey! I'd love to chat about that. I've been really into hiking lately!"
            ),
        )

        resp = client.post(
            f"/chat?session_id={session_id}",
            json={
                "message": "What do you like to do on weekends?",
                "conversation_history": [],
            },
        )
        assert resp.status_code == 200
        chat_data = resp.json()
        assert "response" in chat_data
        assert len(chat_data["response"]) > 0

        # -- Step 6: Email reply --
        monkeypatch.setattr(
            "backend.main.generate_email_reply",
            lambda profile, original_subject, original_body, sender_name, additional_context: (
                "Hi John,\n\nThanks for reaching out! I'd be happy to discuss the project.\n\nBest,\nTest User"
            ),
        )

        resp = client.post(
            f"/email/reply?session_id={session_id}",
            json={
                "original_email_subject": "Project Discussion",
                "original_email_body": "Hi, can we discuss the project timeline?",
                "sender_name": "John",
                "additional_context": "I'm available next week",
            },
        )
        assert resp.status_code == 200
        reply_data = resp.json()
        assert "reply" in reply_data
        assert "John" in reply_data["reply"]

        # Cleanup
        _sessions.pop(session_id, None)


class TestEndToEndProfileBuild:
    """Test the profile building pipeline with mocked external services."""

    def test_profile_build_with_mocked_gmail_and_openai(self, client, monkeypatch):
        """Test profile/build with mocked Gmail fetch and OpenAI extraction."""
        from backend.models.schemas import EmailMessage

        session_id = "e2e-profile-build"
        _sessions[session_id] = {
            "credentials": {
                "token": "fake",
                "refresh_token": "fake",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "fake",
                "client_secret": "fake",
                "scopes": [],
            },
            "email": "alice@example.com",
            "profile": None,
        }

        # Mock fetch_emails to return sample data
        monkeypatch.setattr(
            "backend.main.fetch_emails",
            lambda creds, max_results: [
                EmailMessage(
                    message_id="e1",
                    subject="Yoga class tomorrow",
                    sender="Alice <alice@example.com>",
                    recipient="studio@yoga.com",
                    body="Hi, is there space in the 9am class tomorrow?",
                ),
                EmailMessage(
                    message_id="e2",
                    subject="Re: Team lunch",
                    sender="Alice <alice@example.com>",
                    recipient="team@work.com",
                    body="Sounds good! I love the new sushi place downtown.",
                ),
                EmailMessage(
                    message_id="e3",
                    subject="Your Amazon order",
                    sender="ship-confirm@amazon.com",
                    recipient="alice@example.com",
                    body="Your order of Yoga Mat Premium has been delivered.",
                ),
            ],
        )

        # Mock build_profile to return a profile based on the emails
        monkeypatch.setattr(
            "backend.main.build_profile",
            lambda emails, user_email: UserProfile(
                email=user_email,
                name="Alice",
                personality_traits=["health-conscious", "social", "organized"],
                hobbies=["yoga", "dining out"],
                interests=["fitness", "food"],
                communication_style="polite and concise",
                frequently_discussed_topics=["yoga", "team activities"],
                purchase_categories=["fitness equipment"],
                writing_tone="friendly and professional",
                summary="A health-conscious professional who enjoys yoga and social dining.",
            ),
        )

        resp = client.post(
            f"/profile/build?session_id={session_id}",
            json={"max_emails": 50},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email_count"] == 3
        assert data["profile"]["name"] == "Alice"
        assert "yoga" in data["profile"]["hobbies"]
        assert "fitness equipment" in data["profile"]["purchase_categories"]

        # Verify profile was stored in session
        resp = client.get(f"/profile?session_id={session_id}")
        assert resp.status_code == 200
        assert resp.json()["profile"]["name"] == "Alice"

        _sessions.pop(session_id, None)

    def test_profile_build_no_emails_returns_404(self, client, monkeypatch):
        """Test that building a profile with no emails returns 404."""
        session_id = "e2e-no-emails"
        _sessions[session_id] = {
            "credentials": {
                "token": "fake",
                "refresh_token": "fake",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "fake",
                "client_secret": "fake",
                "scopes": [],
            },
            "email": "empty@example.com",
            "profile": None,
        }

        monkeypatch.setattr(
            "backend.main.fetch_emails",
            lambda creds, max_results: [],
        )

        resp = client.post(
            f"/profile/build?session_id={session_id}",
            json={"max_emails": 100},
        )
        assert resp.status_code == 404
        assert "No emails found" in resp.json()["detail"]

        _sessions.pop(session_id, None)


class TestEndToEndChat:
    """Test the chat functionality end-to-end."""

    def test_chat_conversation_with_history(self, client, authenticated_session, monkeypatch):
        """Test a multi-turn chat conversation."""
        turn = 0
        responses = [
            "Hey! I love weekends. Usually I go hiking or read a good book.",
            "Oh definitely! I just finished 'Thinking, Fast and Slow'. Highly recommend it!",
            "For trails, I'd suggest checking out the ridge trail. Amazing views!",
        ]

        def mock_chat(profile, message, conversation_history):
            nonlocal turn
            resp = responses[min(turn, len(responses) - 1)]
            turn += 1
            return resp

        monkeypatch.setattr("backend.main.generate_chat_response", mock_chat)

        sid = authenticated_session
        history = []

        # Turn 1
        resp = client.post(
            f"/chat?session_id={sid}",
            json={"message": "What do you like to do?", "conversation_history": history},
        )
        assert resp.status_code == 200
        reply1 = resp.json()["response"]
        assert "hiking" in reply1.lower() or "read" in reply1.lower()
        history.append({"role": "user", "content": "What do you like to do?"})
        history.append({"role": "assistant", "content": reply1})

        # Turn 2
        resp = client.post(
            f"/chat?session_id={sid}",
            json={"message": "Any book recommendations?", "conversation_history": history},
        )
        assert resp.status_code == 200
        reply2 = resp.json()["response"]
        assert len(reply2) > 0
        history.append({"role": "user", "content": "Any book recommendations?"})
        history.append({"role": "assistant", "content": reply2})

        # Turn 3
        resp = client.post(
            f"/chat?session_id={sid}",
            json={"message": "What about hiking trails?", "conversation_history": history},
        )
        assert resp.status_code == 200
        reply3 = resp.json()["response"]
        assert len(reply3) > 0

    def test_chat_requires_profile(self, client, unauthenticated_session):
        """Test that chat fails gracefully without a built profile."""
        resp = client.post(
            f"/chat?session_id={unauthenticated_session}",
            json={"message": "Hello!"},
        )
        assert resp.status_code == 400
        assert "Profile not built" in resp.json()["detail"]


class TestEndToEndEmailReply:
    """Test the email reply functionality end-to-end."""

    def test_generate_email_reply(self, client, authenticated_session, monkeypatch):
        """Test generating an email reply in the user's style."""
        monkeypatch.setattr(
            "backend.main.generate_email_reply",
            lambda profile, original_subject, original_body, sender_name, additional_context: (
                "Hi Sarah,\n\n"
                "Thanks for the invite! I'd love to join the team dinner.\n"
                "I'm free after 6pm so that works perfectly.\n\n"
                "Looking forward to it!\n"
                "Test User"
            ),
        )

        resp = client.post(
            f"/email/reply?session_id={authenticated_session}",
            json={
                "original_email_subject": "Team dinner this Friday",
                "original_email_body": "Hi everyone, want to do a team dinner this Friday at 7pm?",
                "sender_name": "Sarah",
                "additional_context": "I'm free after 6pm",
            },
        )
        assert resp.status_code == 200
        reply = resp.json()["reply"]
        assert "Sarah" in reply
        assert "dinner" in reply.lower()

    def test_email_reply_without_optional_fields(self, client, authenticated_session, monkeypatch):
        """Test email reply works with only required fields."""
        monkeypatch.setattr(
            "backend.main.generate_email_reply",
            lambda profile, original_subject, original_body, sender_name, additional_context: (
                "Thanks for reaching out! I'll look into this."
            ),
        )

        resp = client.post(
            f"/email/reply?session_id={authenticated_session}",
            json={
                "original_email_subject": "Quick question",
                "original_email_body": "Can you review this document?",
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["reply"]) > 0

    def test_email_reply_requires_profile(self, client, unauthenticated_session):
        """Test that email reply fails gracefully without a built profile."""
        resp = client.post(
            f"/email/reply?session_id={unauthenticated_session}",
            json={
                "original_email_subject": "Test",
                "original_email_body": "Hello",
            },
        )
        assert resp.status_code == 400
        assert "Profile not built" in resp.json()["detail"]


class TestEndToEndProfileBuilderIntegration:
    """Test the profile builder module integration with mocked OpenAI."""

    def test_build_profile_with_mock_openai(self, sample_emails):
        """Test build_profile() with a mocked OpenAI client."""
        mock_response = make_mock_openai_response(_FAKE_PROFILE_JSON)

        with patch("backend.profile_builder.builder.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            MockOpenAI.return_value = mock_client

            from backend.profile_builder.builder import build_profile

            profile = build_profile(
                sample_emails,
                "test@example.com",
                openai_api_key="fake-key",
            )

            assert profile.email == "test@example.com"
            assert profile.name == "Test User"
            assert "friendly" in profile.personality_traits
            assert "hiking" in profile.hobbies
            assert "technology" in profile.interests
            assert profile.communication_style == "casual and warm"
            assert profile.writing_tone == "friendly and informal"

            # Verify OpenAI was called
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args
            messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
            assert any("test@example.com" in m["content"] for m in messages)


class TestEndToEndResponderIntegration:
    """Test the LLM responder module integration with mocked OpenAI."""

    def test_generate_chat_response_with_mock_openai(self, sample_profile):
        """Test generate_chat_response() with a mocked OpenAI client."""
        expected_reply = "I love hiking! There's nothing like being out in nature."
        mock_response = make_mock_openai_response(expected_reply)

        with patch("backend.llm.responder.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            MockOpenAI.return_value = mock_client

            from backend.llm.responder import generate_chat_response

            response = generate_chat_response(
                profile=sample_profile,
                message="What are your hobbies?",
                openai_api_key="fake-key",
            )

            assert response == expected_reply
            mock_client.chat.completions.create.assert_called_once()

            # Verify system prompt includes profile info
            call_kwargs = mock_client.chat.completions.create.call_args
            messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
            system_msg = messages[0]["content"]
            assert "Test User" in system_msg
            assert "hiking" in system_msg

    def test_generate_chat_response_with_history(self, sample_profile):
        """Test that conversation history is passed to the LLM."""
        mock_response = make_mock_openai_response("Great question!")

        with patch("backend.llm.responder.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            MockOpenAI.return_value = mock_client

            from backend.llm.responder import generate_chat_response
            from backend.models.schemas import ChatMessage

            history = [
                ChatMessage(role="user", content="Hi there!"),
                ChatMessage(role="assistant", content="Hello! How can I help?"),
            ]

            generate_chat_response(
                profile=sample_profile,
                message="Tell me more",
                conversation_history=history,
                openai_api_key="fake-key",
            )

            call_kwargs = mock_client.chat.completions.create.call_args
            messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
            # system + 2 history + 1 new = 4 messages
            assert len(messages) == 4
            assert messages[1]["content"] == "Hi there!"
            assert messages[2]["content"] == "Hello! How can I help?"
            assert messages[3]["content"] == "Tell me more"

    def test_generate_email_reply_with_mock_openai(self, sample_profile):
        """Test generate_email_reply() with a mocked OpenAI client."""
        expected_reply = "Hi John,\nThanks for reaching out!\nBest, Test User"
        mock_response = make_mock_openai_response(expected_reply)

        with patch("backend.llm.responder.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            MockOpenAI.return_value = mock_client

            from backend.llm.responder import generate_email_reply

            reply = generate_email_reply(
                profile=sample_profile,
                original_subject="Meeting Tomorrow",
                original_body="Can we meet at 3pm?",
                sender_name="John",
                additional_context="I prefer morning meetings",
                openai_api_key="fake-key",
            )

            assert reply == expected_reply
            mock_client.chat.completions.create.assert_called_once()

            # Verify the prompt includes email details
            call_kwargs = mock_client.chat.completions.create.call_args
            messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
            user_msg = messages[1]["content"]
            assert "Meeting Tomorrow" in user_msg
            assert "John" in user_msg
            assert "morning meetings" in user_msg


class TestEndToEndEdgeCases:
    """Test edge cases in the end-to-end flow."""

    def test_invalid_session_id(self, client):
        """Test that all authenticated endpoints reject invalid session IDs."""
        endpoints = [
            ("GET", "/profile?session_id=invalid"),
            ("POST", "/chat?session_id=invalid"),
            ("POST", "/email/reply?session_id=invalid"),
            ("POST", "/profile/build?session_id=invalid"),
        ]

        for method, url in endpoints:
            if method == "GET":
                resp = client.get(url)
            else:
                resp = client.post(url, json={
                    "message": "test",
                    "original_email_subject": "test",
                    "original_email_body": "test",
                    "max_emails": 10,
                })
            assert resp.status_code == 401, f"Expected 401 for {method} {url}, got {resp.status_code}"

    def test_frontend_loads(self, client):
        """Test that the frontend HTML page loads and contains key elements."""
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        assert "Digital You" in html
        assert "Connect Gmail Account" in html
        assert "chat-input" in html
        assert "email-reply" in html

    def test_health_check(self, client):
        """Test the health endpoint returns ok."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

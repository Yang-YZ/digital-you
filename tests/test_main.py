"""Tests for the FastAPI application endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app, _sessions
from backend.models.schemas import UserProfile


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def authenticated_session():
    """Create a fake authenticated session with a profile."""
    session_id = "test-session-123"
    profile = UserProfile(
        email="test@example.com",
        name="Test User",
        personality_traits=["friendly"],
        hobbies=["reading"],
        interests=["technology"],
        communication_style="casual",
        writing_tone="warm",
        summary="A friendly tech enthusiast.",
    )
    _sessions[session_id] = {
        "credentials": {
            "token": "fake-token",
            "refresh_token": "fake-refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "fake-id",
            "client_secret": "fake-secret",
            "scopes": [],
        },
        "email": "test@example.com",
        "profile": profile,
    }
    yield session_id
    _sessions.pop(session_id, None)


class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAuthentication:
    def test_login_returns_auth_url(self, client, monkeypatch):
        monkeypatch.setattr(
            "backend.main.get_authorization_url",
            lambda: ("https://accounts.google.com/o/oauth2/auth?test=1", "test-state"),
        )
        monkeypatch.setattr("backend.main.GOOGLE_CLIENT_ID", "fake-id")
        monkeypatch.setattr("backend.main.GOOGLE_CLIENT_SECRET", "fake-secret")
        response = client.get("/auth/login")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "accounts.google.com" in data["auth_url"]

    def test_login_fails_without_client_id(self, client, monkeypatch):
        monkeypatch.setattr("backend.main.GOOGLE_CLIENT_ID", "")
        monkeypatch.setattr("backend.main.GOOGLE_CLIENT_SECRET", "fake-secret")
        response = client.get("/auth/login")
        assert response.status_code == 500
        assert "GOOGLE_CLIENT_ID" in response.json()["detail"]

    def test_login_fails_without_client_secret(self, client, monkeypatch):
        monkeypatch.setattr("backend.main.GOOGLE_CLIENT_ID", "fake-id")
        monkeypatch.setattr("backend.main.GOOGLE_CLIENT_SECRET", "")
        response = client.get("/auth/login")
        assert response.status_code == 500
        assert "GOOGLE_CLIENT_SECRET" in response.json()["detail"]


class TestProfile:
    def test_get_profile_without_session(self, client):
        response = client.get("/profile?session_id=nonexistent")
        assert response.status_code == 401

    def test_get_profile_without_building(self, client):
        _sessions["no-profile"] = {
            "credentials": {},
            "email": "test@example.com",
            "profile": None,
        }
        response = client.get("/profile?session_id=no-profile")
        assert response.status_code == 400
        _sessions.pop("no-profile", None)

    def test_get_profile_success(self, client, authenticated_session):
        response = client.get(f"/profile?session_id={authenticated_session}")
        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["email"] == "test@example.com"
        assert data["profile"]["name"] == "Test User"


class TestChat:
    def test_chat_without_session(self, client):
        response = client.post(
            "/chat?session_id=nonexistent",
            json={"message": "hello"},
        )
        assert response.status_code == 401

    def test_chat_without_profile(self, client):
        _sessions["no-profile"] = {
            "credentials": {},
            "email": "test@example.com",
            "profile": None,
        }
        response = client.post(
            "/chat?session_id=no-profile",
            json={"message": "hello"},
        )
        assert response.status_code == 400
        _sessions.pop("no-profile", None)


class TestEmailReply:
    def test_email_reply_without_session(self, client):
        response = client.post(
            "/email/reply?session_id=nonexistent",
            json={
                "original_email_subject": "Test",
                "original_email_body": "Hello",
            },
        )
        assert response.status_code == 401


class TestFrontend:
    def test_serves_frontend(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Digital You" in response.text

    def test_serves_frontend_with_utf8_emojis(self, client):
        """Ensure the HTML is read as UTF-8 so emoji chars don't break on Windows."""
        response = client.get("/")
        assert response.status_code == 200
        # The index.html contains emoji characters that would fail under cp1252
        assert "🤖" in response.text

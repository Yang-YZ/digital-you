"""Digital You — FastAPI application entry point."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.auth.gmail_auth import (
    credentials_from_dict,
    credentials_to_dict,
    exchange_code_for_credentials,
    get_authorization_url,
)
from backend.config import FRONTEND_URL, MAX_EMAILS_TO_FETCH
from backend.email_processor.processor import (
    categorize_emails,
    fetch_emails,
    get_user_email,
)
from backend.llm.responder import generate_chat_response, generate_email_reply
from backend.models.schemas import (
    AuthURL,
    ChatRequest,
    EmailReplyRequest,
    ProfileBuildRequest,
    ProfileResponse,
    UserProfile,
)
from backend.profile_builder.builder import build_profile

app = FastAPI(
    title="Digital You",
    description="Build an AI representative from your email history",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (for demo purposes — use a database in production)
_sessions: dict[str, dict[str, Any]] = {}

# Serve the frontend static files
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")


# ---------------------------------------------------------------------------
# Helper: simple session management
# ---------------------------------------------------------------------------

def _get_session(session_id: str) -> dict[str, Any]:
    if session_id not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in first.")
    return _sessions[session_id]


def _get_profile(session_id: str) -> UserProfile:
    session = _get_session(session_id)
    profile = session.get("profile")
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="Profile not built yet. Please build your profile first.",
        )
    return profile


# ---------------------------------------------------------------------------
# Routes: Frontend
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_frontend() -> HTMLResponse:
    """Serve the main frontend page."""
    index_path = _frontend_dir / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)
    return HTMLResponse(index_path.read_text())


# ---------------------------------------------------------------------------
# Routes: Authentication
# ---------------------------------------------------------------------------

@app.get("/auth/login", response_model=AuthURL)
async def auth_login() -> AuthURL:
    """Start the OAuth2 login flow. Returns the Google authorization URL."""
    auth_url, state = get_authorization_url()
    # Store state for later verification
    _sessions[state] = {"state": state}
    return AuthURL(auth_url=auth_url)


@app.get("/auth/callback")
async def auth_callback(code: str, state: str) -> dict[str, str]:
    """Handle the OAuth2 callback from Google.

    Exchanges the authorization code for credentials and creates a session.
    """
    credentials = exchange_code_for_credentials(code)
    creds_dict = credentials_to_dict(credentials)
    user_email = get_user_email(credentials)

    session_id = state  # Use the OAuth state as session ID
    _sessions[session_id] = {
        "credentials": creds_dict,
        "email": user_email,
        "profile": None,
    }

    return {"session_id": session_id, "email": user_email}


# ---------------------------------------------------------------------------
# Routes: Profile Building
# ---------------------------------------------------------------------------

@app.post("/profile/build", response_model=ProfileResponse)
async def build_user_profile(
    request: ProfileBuildRequest,
    session_id: str,
) -> ProfileResponse:
    """Fetch emails and build the user's personality profile."""
    session = _get_session(session_id)
    credentials = credentials_from_dict(session["credentials"])
    user_email = session["email"]

    max_emails = min(request.max_emails, MAX_EMAILS_TO_FETCH)

    # Fetch emails
    emails = fetch_emails(credentials, max_results=max_emails)
    if not emails:
        raise HTTPException(status_code=404, detail="No emails found in your account.")

    # Build profile
    profile = build_profile(emails, user_email)

    # Store profile in session
    session["profile"] = profile

    return ProfileResponse(profile=profile, email_count=len(emails))


@app.get("/profile", response_model=ProfileResponse)
async def get_profile(session_id: str) -> ProfileResponse:
    """Get the current user's profile."""
    profile = _get_profile(session_id)
    return ProfileResponse(profile=profile)


# ---------------------------------------------------------------------------
# Routes: Chat & Email Reply
# ---------------------------------------------------------------------------

@app.post("/chat")
async def chat(request: ChatRequest, session_id: str) -> dict[str, str]:
    """Chat with the user's digital representative."""
    profile = _get_profile(session_id)

    response = generate_chat_response(
        profile=profile,
        message=request.message,
        conversation_history=request.conversation_history,
    )

    return {"response": response}


@app.post("/email/reply")
async def email_reply(
    request: EmailReplyRequest,
    session_id: str,
) -> dict[str, str]:
    """Generate an email reply in the user's style."""
    profile = _get_profile(session_id)

    reply = generate_email_reply(
        profile=profile,
        original_subject=request.original_email_subject,
        original_body=request.original_email_body,
        sender_name=request.sender_name,
        additional_context=request.additional_context,
    )

    return {"reply": reply}


# ---------------------------------------------------------------------------
# Routes: Health Check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# App runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    from backend.config import APP_HOST, APP_PORT

    uvicorn.run("backend.main:app", host=APP_HOST, port=APP_PORT, reload=True)

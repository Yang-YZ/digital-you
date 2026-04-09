"""Pydantic models for the application."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    """Represents a single email message."""

    message_id: str
    subject: str = ""
    sender: str = ""
    recipient: str = ""
    date: str = ""
    body: str = ""
    snippet: str = ""


class UserProfile(BaseModel):
    """Extracted personality profile from email history."""

    email: str
    name: str = ""
    personality_traits: list[str] = Field(default_factory=list)
    hobbies: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    communication_style: str = ""
    frequently_discussed_topics: list[str] = Field(default_factory=list)
    purchase_categories: list[str] = Field(default_factory=list)
    writing_tone: str = ""
    summary: str = ""


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    message: str
    conversation_history: list[ChatMessage] = Field(default_factory=list)


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str


class EmailReplyRequest(BaseModel):
    """Request body for generating an email reply."""

    original_email_subject: str
    original_email_body: str
    sender_name: str = ""
    additional_context: str = ""


class ProfileBuildRequest(BaseModel):
    """Request to build/rebuild a user profile."""

    max_emails: int = 500


class AuthURL(BaseModel):
    """Response containing the OAuth2 authorization URL."""

    auth_url: str


class ProfileResponse(BaseModel):
    """Response containing the user profile."""

    profile: UserProfile
    email_count: int = 0


# Rebuild forward references so ChatRequest can use ChatMessage
ChatRequest.model_rebuild()

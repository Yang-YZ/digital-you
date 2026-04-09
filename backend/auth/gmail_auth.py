"""Gmail OAuth2 authentication handling."""

from __future__ import annotations

import json
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from backend.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_SCOPES,
)


def _build_client_config() -> dict[str, Any]:
    """Build the OAuth2 client configuration dictionary."""
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }


def get_authorization_url() -> tuple[str, str]:
    """Generate the Google OAuth2 authorization URL.

    Returns:
        A tuple of (authorization_url, state).
    """
    flow = Flow.from_client_config(
        _build_client_config(),
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url, state


def exchange_code_for_credentials(code: str) -> Credentials:
    """Exchange an authorization code for OAuth2 credentials.

    Args:
        code: The authorization code from the OAuth2 callback.

    Returns:
        Google OAuth2 Credentials object.
    """
    flow = Flow.from_client_config(
        _build_client_config(),
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_to_dict(credentials: Credentials) -> dict[str, Any]:
    """Serialize credentials to a dictionary for storage.

    Args:
        credentials: Google OAuth2 Credentials object.

    Returns:
        Dictionary representation of the credentials.
    """
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes) if credentials.scopes else [],
    }


def credentials_from_dict(creds_dict: dict[str, Any]) -> Credentials:
    """Deserialize credentials from a dictionary.

    Args:
        creds_dict: Dictionary representation of credentials.

    Returns:
        Google OAuth2 Credentials object.
    """
    return Credentials(
        token=creds_dict["token"],
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes"),
    )


def credentials_to_json(credentials: Credentials) -> str:
    """Serialize credentials to a JSON string."""
    return json.dumps(credentials_to_dict(credentials))


def credentials_from_json(json_str: str) -> Credentials:
    """Deserialize credentials from a JSON string."""
    return credentials_from_dict(json.loads(json_str))

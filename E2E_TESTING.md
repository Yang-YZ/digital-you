# End-to-End Testing Guide

This guide explains how to test Digital You end-to-end, covering both automated
tests (with mocked services) and manual testing with real credentials.

---

## Quick Start: Automated E2E Tests

Run all tests, including the end-to-end suite, with a single command:

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run only E2E tests
pytest tests/test_e2e.py -v
```

No API keys or credentials are needed — external services (Gmail API, OpenAI)
are fully mocked.

---

## What the E2E Tests Cover

| Test Class | What It Tests |
|---|---|
| `TestEndToEndUserFlow` | Complete journey: login → OAuth callback → build profile → get profile → chat → email reply |
| `TestEndToEndProfileBuild` | Profile building with mocked emails, and the "no emails" edge case |
| `TestEndToEndChat` | Multi-turn chat conversations with conversation history |
| `TestEndToEndEmailReply` | Email reply generation with required and optional fields |
| `TestEndToEndProfileBuilderIntegration` | `build_profile()` function with mocked OpenAI API |
| `TestEndToEndResponderIntegration` | `generate_chat_response()` and `generate_email_reply()` with mocked OpenAI API |
| `TestEndToEndEdgeCases` | Invalid sessions, frontend loading, health check |

---

## Manual E2E Testing with Real Credentials

To test with real Gmail and OpenAI integration:

### Prerequisites

1. **OpenAI API key** — Get one at <https://platform.openai.com/api-keys>
2. **Google Cloud project** with the Gmail API enabled and OAuth 2.0 credentials

### Step 1: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your real credentials:

```env
OPENAI_API_KEY=sk-...your-real-key...
GOOGLE_CLIENT_ID=...your-client-id...
GOOGLE_CLIENT_SECRET=...your-client-secret...
APP_SECRET_KEY=any-random-string
```

### Step 2: Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable the **Gmail API**
4. Go to **APIs & Services → Credentials**
5. Create an **OAuth 2.0 Client ID** (type: Web application)
6. Add `http://localhost:8000/auth/callback` as an **Authorized redirect URI**
7. Copy the Client ID and Client Secret to your `.env`

### Step 3: Start the Server

```bash
python -m backend.main
```

The server starts at <http://localhost:8000>.

### Step 4: Walk Through the Flow

1. **Open** <http://localhost:8000> in your browser
2. **Click** "Connect Gmail Account" — you'll be redirected to Google
3. **Sign in** and grant read-only Gmail access
4. **Click** "Build / Rebuild Profile" — the app fetches your emails and extracts your personality
5. **Review** the personality profile dashboard (traits, hobbies, interests, etc.)
6. **Chat tab** — type messages and see responses in your style
7. **Email Reply tab** — paste an email you received and generate a reply

### What to Verify

- [ ] OAuth login redirects to Google and returns successfully
- [ ] Profile shows realistic personality traits extracted from your emails
- [ ] Chat responses match your communication style
- [ ] Email replies are written in your tone and reference your interests naturally
- [ ] Error states work correctly (e.g., chatting before building a profile)

---

## Test Architecture

### Mocking Strategy

The E2E tests mock external services at two levels:

**API route level** (in `test_e2e.py`):
- `backend.main.fetch_emails` — returns pre-built `EmailMessage` objects
- `backend.main.build_profile` — returns a pre-built `UserProfile`
- `backend.main.generate_chat_response` — returns canned chat responses
- `backend.main.generate_email_reply` — returns canned email replies
- `backend.main.get_authorization_url` — returns a fake Google auth URL
- `backend.main.exchange_code_for_credentials` — returns fake credentials
- `backend.main.get_user_email` — returns a fake email address

**Module level** (in integration tests):
- `backend.profile_builder.builder.OpenAI` — mock OpenAI client for profile extraction
- `backend.llm.responder.OpenAI` — mock OpenAI client for response generation

### Shared Fixtures (`tests/conftest.py`)

| Fixture | Description |
|---|---|
| `client` | FastAPI `TestClient` for making HTTP requests |
| `sample_profile` | A pre-built `UserProfile` with realistic data |
| `sample_emails` | A list of 5 sample `EmailMessage` objects |
| `authenticated_session` | A session with credentials and a built profile |
| `unauthenticated_session` | A session with credentials but no profile |
| `make_mock_openai_response()` | Helper to create mock OpenAI API responses |

---

## Adding New E2E Tests

Follow this pattern:

```python
class TestMyFeature:
    def test_my_scenario(self, client, authenticated_session, monkeypatch):
        # Mock any external calls
        monkeypatch.setattr(
            "backend.main.generate_chat_response",
            lambda profile, message, conversation_history: "Mocked response",
        )

        # Make the API call
        resp = client.post(
            f"/chat?session_id={authenticated_session}",
            json={"message": "Hello!"},
        )

        # Assert the result
        assert resp.status_code == 200
        assert resp.json()["response"] == "Mocked response"
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'backend'` | Run tests from the project root: `cd digital-you && pytest tests/ -v` |
| OAuth redirect fails locally | Ensure `http://localhost:8000/auth/callback` is in your Google Cloud authorized redirect URIs |
| "Profile not built yet" error | Build the profile first before chatting or generating replies |
| OpenAI API errors | Check that your `OPENAI_API_KEY` is valid and has credits |
| Tests fail with import errors | Run `pip install -r requirements.txt` to install dependencies |

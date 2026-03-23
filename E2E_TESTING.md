# Local Testing Guide

How to test Digital You end-to-end on your local machine, entirely from your
terminal.

---

## Prerequisites

- Python 3.11+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A Google Cloud project with the Gmail API enabled and OAuth 2.0 credentials
  (see [README → Google Cloud Setup](README.md#3-google-cloud-setup))

---

## 1. Install & Configure

```bash
# Clone (skip if you already have it)
git clone https://github.com/Yang-YZ/digital-you.git
cd digital-you

# Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Now edit .env with your real keys:
#   OPENAI_API_KEY=sk-...
#   GOOGLE_CLIENT_ID=...
#   GOOGLE_CLIENT_SECRET=...
#   APP_SECRET_KEY=some-random-string
```

---

## 2. Start the Server

```bash
python -m backend.main
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
```

Leave this running. Open a **second terminal** (activate the same venv) for the
steps below.

---

## 3. Verify the Server Is Running

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

---

## 4. Test the Auth Flow (Login)

```bash
curl http://localhost:8000/auth/login
```

Expected response (a Google OAuth URL):

```json
{"auth_url":"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=...&redirect_uri=...&scope=...&state=SOME_STATE&access_type=offline&include_granted_scopes=true&prompt=consent"}
```

**Next — complete the OAuth flow:**

1. Copy the `auth_url` value and open it in your browser.
2. Sign in with your Google account and grant access.
3. Google redirects you to `http://localhost:8000/auth/callback?code=...&state=...`.
4. The browser page shows JSON with your `session_id` and `email`. **Copy the
   `session_id`** — you'll need it for every subsequent request.

> **Tip:** If the redirect page shows JSON directly, just grab `session_id`
> from it. If the frontend handles the redirect, check the URL bar or
> `localStorage` in the browser console for `session_id`.

Save it in your terminal for convenience:

```bash
export SESSION_ID="<paste-your-session-id-here>"
```

---

## 5. Build Your Profile

This fetches your recent emails and uses OpenAI to extract a personality
profile:

```bash
curl -X POST "http://localhost:8000/profile/build?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"max_emails": 50}'
```

Expected response (truncated):

```json
{
  "profile": {
    "email": "you@gmail.com",
    "name": "Your Name",
    "personality_traits": ["curious", "friendly", ...],
    "hobbies": ["reading", "cooking", ...],
    "interests": ["technology", "travel", ...],
    "communication_style": "casual and warm",
    "frequently_discussed_topics": ["work", "travel", ...],
    "purchase_categories": ["books", "electronics", ...],
    "writing_tone": "friendly and informal",
    "summary": "A curious tech enthusiast who ..."
  },
  "email_count": 50
}
```

> **Note:** Use a smaller `max_emails` value (e.g. `10`) for faster testing.
> The default limit is 500.

---

## 6. Retrieve Your Profile

```bash
curl "http://localhost:8000/profile?session_id=$SESSION_ID"
```

Returns the same profile you built in the previous step.

---

## 7. Chat with Your Digital Twin

```bash
curl -X POST "http://localhost:8000/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"message": "What do you like to do on weekends?"}'
```

Expected response:

```json
{"response":"Hey! I usually love to..."}
```

### Multi-turn conversation

Pass `conversation_history` to continue the conversation:

```bash
curl -X POST "http://localhost:8000/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Any book recommendations?",
    "conversation_history": [
      {"role": "user", "content": "What do you like to do on weekends?"},
      {"role": "assistant", "content": "Hey! I usually love to read or go hiking..."}
    ]
  }'
```

---

## 8. Generate an Email Reply

```bash
curl -X POST "http://localhost:8000/email/reply?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "original_email_subject": "Team dinner this Friday?",
    "original_email_body": "Hi everyone, want to grab dinner this Friday at 7pm?",
    "sender_name": "Sarah",
    "additional_context": "I am free after 6pm"
  }'
```

Expected response:

```json
{"reply":"Hi Sarah,\n\nThat sounds great! I'm free after 6 so Friday at 7 works perfectly..."}
```

`sender_name` and `additional_context` are optional — only `original_email_subject`
and `original_email_body` are required.

---

## 9. Test the Frontend (Browser)

Open <http://localhost:8000> in your browser to use the full UI:

1. Click **"Connect Gmail Account"** → signs in with Google
2. Click **"Build / Rebuild Profile"** → analyzes your emails
3. **Chat tab** → talk to your digital twin
4. **Email Reply tab** → paste an email and generate a reply

---

## 10. Run the Unit Tests

Unit tests don't require any API keys — they test internal logic only:

```bash
pytest tests/ -v
```

---

## Quick Reference

| Endpoint               | Method | What it does                        | Needs session? |
|------------------------|--------|-------------------------------------|----------------|
| `/health`              | GET    | Health check                        | No             |
| `/auth/login`          | GET    | Get Google OAuth URL                | No             |
| `/auth/callback`       | GET    | Handle OAuth callback (automatic)   | No             |
| `/profile/build`       | POST   | Fetch emails & build profile        | Yes            |
| `/profile`             | GET    | Get current profile                 | Yes            |
| `/chat`                | POST   | Chat with your digital twin         | Yes            |
| `/email/reply`         | POST   | Generate an email reply             | Yes            |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `connection refused` on curl | Make sure the server is running (`python -m backend.main`) |
| `{"detail":"Not authenticated"}` | Your session expired or `SESSION_ID` is wrong — redo step 4 |
| `{"detail":"Profile not built yet"}` | Run step 5 first to build your profile |
| OAuth redirect fails | Ensure `http://localhost:8000` is in your Google Cloud authorized redirect URIs |
| OpenAI errors / empty responses | Check that `OPENAI_API_KEY` in `.env` is valid and has credits |
| `ModuleNotFoundError` | Make sure you activated the venv and ran `pip install -r requirements.txt` |

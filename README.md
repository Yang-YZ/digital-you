# Digital You 🤖

Build an AI representative that thinks, writes, and responds like you — powered by your email history.

## Overview

**Digital You** analyzes your Gmail history to extract your personality traits, hobbies, interests, communication style, and purchase patterns. It then uses this profile to power an AI that can:

- **Chat as you** — Have conversations that sound exactly like you
- **Reply to emails** — Generate email drafts in your personal writing style
- **Represent you** — Act as your digital twin in written communication

## How It Works

1. **Connect Gmail** — Securely authenticate with Google OAuth2 (read-only access)
2. **Build Profile** — The app analyzes your sent and received emails to extract:
   - Personality traits (introverted/extroverted, formal/casual, etc.)
   - Hobbies and interests
   - Communication style and writing tone
   - Frequently discussed topics
   - Purchase categories from receipts/confirmations
3. **Interact** — Chat with your digital twin or generate email replies in your style

## Tech Stack

| Layer      | Technology                     |
|------------|--------------------------------|
| Backend    | Python, FastAPI                |
| Frontend   | HTML, CSS, JavaScript          |
| LLM        | OpenAI GPT-4o-mini             |
| Email      | Gmail API (OAuth2, read-only)  |
| Auth       | Google OAuth2                  |

## Project Structure

```
digital-you/
├── backend/
│   ├── main.py                 # FastAPI application & routes
│   ├── config.py               # Environment configuration
│   ├── auth/
│   │   └── gmail_auth.py       # Google OAuth2 authentication
│   ├── email_processor/
│   │   └── processor.py        # Gmail fetching & processing
│   ├── profile_builder/
│   │   └── builder.py          # Personality extraction via LLM
│   ├── llm/
│   │   └── responder.py        # Response generation in user's style
│   └── models/
│       └── schemas.py          # Pydantic data models
├── frontend/
│   ├── index.html              # Main UI
│   ├── styles.css              # Styling
│   └── app.js                  # Frontend logic
├── tests/
│   ├── test_email_processor.py
│   ├── test_profile_builder.py
│   ├── test_llm_responder.py
│   └── test_main.py
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.11+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- Google Cloud project with Gmail API enabled and OAuth2 credentials

### 1. Clone & Install

```bash
git clone https://github.com/Yang-YZ/digital-you.git
cd digital-you
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual keys:
#   OPENAI_API_KEY=sk-...
#   GOOGLE_CLIENT_ID=...
#   GOOGLE_CLIENT_SECRET=...
#   APP_SECRET_KEY=<random-secret>
```

### 3. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Gmail API**
3. Create **OAuth 2.0 Client ID** credentials (Web application)
4. Add `http://localhost:8000/auth/callback` as an authorized redirect URI
5. Copy the Client ID and Client Secret to your `.env` file

### 4. Run

```bash
python -m backend.main
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Running Tests

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Endpoint         | Description                              |
|--------|------------------|------------------------------------------|
| GET    | `/`              | Serve the frontend                       |
| GET    | `/health`        | Health check                             |
| GET    | `/auth/login`    | Get Google OAuth2 authorization URL      |
| GET    | `/auth/callback` | Handle OAuth2 callback                   |
| POST   | `/profile/build` | Fetch emails & build personality profile |
| GET    | `/profile`       | Get the current user's profile           |
| POST   | `/chat`          | Chat with the digital representative     |
| POST   | `/email/reply`   | Generate an email reply in user's style  |

## License

MIT License — see [LICENSE](LICENSE) for details.

"""FastAPI application entrypoint for digital-you."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .chat import chat_as_user
from .imap_client import fetch_emails
from .persona import generate_persona

load_dotenv()

# Configure our app loggers explicitly. uvicorn installs its own root
# handlers before our app loads, so logging.basicConfig() is a no-op.
# We attach our own StreamHandler so digital_you.* loggers always print.
_app_logger = logging.getLogger("digital_you")
if not _app_logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _app_logger.addHandler(_h)
_app_logger.setLevel(logging.INFO)
_app_logger.propagate = False
logger = _app_logger

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
PERSONA_PATH = DATA_DIR / "me.md"
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="digital-you", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set. Add it to your .env file.",
        )
    return key


class GenerateRequest(BaseModel):
    imap_host: str = Field(..., description="e.g. imap.gmail.com")
    imap_port: int = 993
    username: str
    password: str = Field(..., description="App password recommended")
    mailboxes: list[str] = Field(default_factory=lambda: ["INBOX", "Sent"])
    per_mailbox_limit: int = Field(50, ge=1, le=500)
    model: str = "gpt-4o-mini"
    user_hint: Optional[str] = None


class GenerateResponse(BaseModel):
    email_count: int
    persona_md: str
    saved_to: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    model: str = "gpt-4o-mini"


class ChatResponse(BaseModel):
    reply: str


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "persona_exists": PERSONA_PATH.exists()}


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/persona", response_class=PlainTextResponse)
def get_persona() -> str:
    if not PERSONA_PATH.exists():
        raise HTTPException(status_code=404, detail="me.md has not been generated yet.")
    return PERSONA_PATH.read_text(encoding="utf-8")


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    api_key = _require_openai_key()

    try:
        records = fetch_emails(
            host=req.imap_host,
            port=req.imap_port,
            username=req.username,
            password=req.password,
            mailboxes=req.mailboxes,
            per_mailbox_limit=req.per_mailbox_limit,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"IMAP error: {exc}") from exc

    if not records:
        raise HTTPException(
            status_code=400,
            detail="No emails fetched. Check mailbox names and credentials.",
        )

    try:
        persona_md = generate_persona(
            records=records,
            api_key=api_key,
            model=req.model,
            user_hint=req.user_hint,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"OpenAI error: {exc}") from exc

    PERSONA_PATH.write_text(persona_md, encoding="utf-8")
    return GenerateResponse(
        email_count=len(records),
        persona_md=persona_md,
        saved_to=str(PERSONA_PATH),
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    api_key = _require_openai_key()
    if not PERSONA_PATH.exists():
        raise HTTPException(status_code=400, detail="Generate me.md first.")
    persona_md = PERSONA_PATH.read_text(encoding="utf-8")
    try:
        reply = chat_as_user(
            persona_md=persona_md,
            history=[m.model_dump() for m in req.history],
            user_message=req.message,
            api_key=api_key,
            model=req.model,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"OpenAI error: {exc}") from exc
    return ChatResponse(reply=reply)


# Serve the frontend at "/"
if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))

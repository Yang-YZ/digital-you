"""Profile builder that extracts personality traits from email history."""

from __future__ import annotations

import json

from openai import OpenAI

from backend.config import OPENAI_API_KEY
from backend.models.schemas import EmailMessage, UserProfile

_EXTRACTION_SYSTEM_PROMPT = """You are an expert psychologist and behavioral analyst.
Analyze the following collection of emails sent and received by a user and extract a
comprehensive personality profile. Focus on:

1. **Personality traits**: Are they introverted/extroverted, formal/casual, detail-oriented, etc.
2. **Hobbies and interests**: What do they spend time on, talk about, or purchase?
3. **Communication style**: How do they write? Formal, casual, verbose, concise?
4. **Writing tone**: Friendly, professional, humorous, serious?
5. **Frequently discussed topics**: Work, travel, fitness, technology, etc.
6. **Purchase categories**: What types of products/services do they buy (from receipts/confirmations)?

Return a JSON object with these exact keys:
{
    "name": "the user's apparent name",
    "personality_traits": ["trait1", "trait2", ...],
    "hobbies": ["hobby1", "hobby2", ...],
    "interests": ["interest1", "interest2", ...],
    "communication_style": "description of how they communicate",
    "frequently_discussed_topics": ["topic1", "topic2", ...],
    "purchase_categories": ["category1", "category2", ...],
    "writing_tone": "description of their writing tone",
    "summary": "A 2-3 sentence summary of this person's personality and lifestyle"
}

Return ONLY valid JSON, no additional text."""


def _prepare_email_summary(
    emails: list[EmailMessage],
    max_chars: int = 50000,
) -> str:
    """Prepare a summarized text of emails for the LLM to analyze.

    Args:
        emails: List of email messages.
        max_chars: Maximum total characters to include.

    Returns:
        A formatted string summarizing the emails.
    """
    parts: list[str] = []
    total_chars = 0

    for msg in emails:
        entry = f"Subject: {msg.subject}\nFrom: {msg.sender}\nTo: {msg.recipient}\n"
        if msg.body:
            entry += f"Body: {msg.body}\n"
        elif msg.snippet:
            entry += f"Snippet: {msg.snippet}\n"
        entry += "---\n"

        if total_chars + len(entry) > max_chars:
            break
        parts.append(entry)
        total_chars += len(entry)

    return "\n".join(parts)


def build_profile(
    emails: list[EmailMessage],
    user_email: str,
    openai_api_key: str | None = None,
) -> UserProfile:
    """Analyze emails and build a user personality profile.

    Args:
        emails: List of email messages from the user's account.
        user_email: The user's email address.
        openai_api_key: Optional API key override.

    Returns:
        A UserProfile with extracted personality information.
    """
    api_key = openai_api_key or OPENAI_API_KEY
    client = OpenAI(api_key=api_key)

    email_text = _prepare_email_summary(emails)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Here are the emails for user {user_email}:\n\n{email_text}"
                ),
            },
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)

    return UserProfile(
        email=user_email,
        name=data.get("name", ""),
        personality_traits=data.get("personality_traits", []),
        hobbies=data.get("hobbies", []),
        interests=data.get("interests", []),
        communication_style=data.get("communication_style", ""),
        frequently_discussed_topics=data.get("frequently_discussed_topics", []),
        purchase_categories=data.get("purchase_categories", []),
        writing_tone=data.get("writing_tone", ""),
        summary=data.get("summary", ""),
    )

"""Persona generation from a corpus of emails using OpenAI."""
from __future__ import annotations

import json
from typing import Iterable

from openai import OpenAI

from .imap_client import EmailRecord


PERSONA_SYSTEM_PROMPT = """You are a profiler that builds a rich, structured
persona of a person based on a sample of their personal email history.
You will receive a list of emails the user has sent and received. Focus
primarily on emails the user *sent* (look at the "from" field) to learn
their authentic voice. Use received emails for context (relationships,
interests, topics).

Produce a Markdown document named me.md with the following sections:

# Me

## Snapshot
A 3-5 sentence summary of who this person is.

## Personality
Bullet points on traits (e.g., curious, warm, dry humor, direct).

## Interests & Hobbies
Topics they care about, hobbies, recurring subject matter.

## Communication Style
- Tone (casual / formal / playful / terse)
- Typical greetings & sign-offs
- Sentence length, punctuation habits, emoji usage
- Common phrases or verbal tics (quote 5-10 short signature phrases verbatim)

## Relationships
Who they talk to most and how the tone differs (work, family, friends).

## Values & Opinions
What they seem to believe in, advocate for, or push back against.

## How to Respond as Me
A concrete instruction block (use second person: "You are…") that another
LLM could follow to imitate this person's voice in email replies.

Be specific and grounded in evidence. Do not invent facts. If the sample
is small, say so. Output ONLY the Markdown — no preface, no code fences.
"""


def _format_emails_for_prompt(records: Iterable[EmailRecord], user_hint: str | None) -> str:
    items = [r.to_compact_dict() for r in records]
    payload = {
        "user_hint": user_hint or "",
        "email_count": len(items),
        "emails": items,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_persona(
    records: list[EmailRecord],
    api_key: str,
    model: str = "gpt-4o-mini",
    user_hint: str | None = None,
) -> str:
    """Send the email sample to OpenAI and return the generated me.md content."""
    if not records:
        raise ValueError("No emails were provided for persona generation.")

    client = OpenAI(api_key=api_key)
    user_payload = _format_emails_for_prompt(records, user_hint)

    response = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Here is a JSON payload with a sample of emails. "
                    "Build the me.md persona document.\n\n" + user_payload
                ),
            },
        ],
    )
    content = response.choices[0].message.content or ""
    return content.strip()

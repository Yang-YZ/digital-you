"""Chat-as-you: respond to messages while imitating the user's persona."""
from __future__ import annotations

from openai import OpenAI


CHAT_SYSTEM_TEMPLATE = """You are roleplaying as a specific person. Their
persona, voice, and communication style are described in the Markdown
document below. Stay in character. Respond as that person would respond
in a casual message or email reply. Match their tone, sentence length,
greeting/sign-off habits, vocabulary, and emoji usage. Do not break
character. Do not mention that you are an AI or that you have a persona
document. If asked something the persona could not plausibly know, answer
the way they would (deflect, joke, or admit it) — don't fabricate facts
about their life.

--- PERSONA DOCUMENT (me.md) ---
{persona_md}
--- END PERSONA DOCUMENT ---
"""


def chat_as_user(
    persona_md: str,
    history: list[dict],
    user_message: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> str:
    """Generate a reply in the user's voice.

    history: list of {"role": "user"|"assistant", "content": str}
    """
    if not persona_md.strip():
        raise ValueError("Persona document is empty. Generate me.md first.")

    client = OpenAI(api_key=api_key)
    messages = [{"role": "system", "content": CHAT_SYSTEM_TEMPLATE.format(persona_md=persona_md)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=model,
        temperature=0.8,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()

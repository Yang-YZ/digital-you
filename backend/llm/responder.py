"""LLM-based responder that generates replies in the user's style."""

from __future__ import annotations

from openai import OpenAI

from backend.config import OPENAI_API_KEY
from backend.models.schemas import ChatMessage, UserProfile


def _build_system_prompt(profile: UserProfile) -> str:
    """Build a system prompt that instructs the LLM to mimic the user.

    Args:
        profile: The user's extracted personality profile.

    Returns:
        A system prompt string.
    """
    traits = ", ".join(profile.personality_traits) if profile.personality_traits else "unknown"
    hobbies = ", ".join(profile.hobbies) if profile.hobbies else "unknown"
    interests = ", ".join(profile.interests) if profile.interests else "unknown"
    topics = (
        ", ".join(profile.frequently_discussed_topics)
        if profile.frequently_discussed_topics
        else "various"
    )

    return f"""You are acting as a digital representative of {profile.name or profile.email}.
You must respond to messages and emails exactly as this person would.

Here is the personality profile you MUST embody:

**Name**: {profile.name or profile.email}
**Personality Traits**: {traits}
**Hobbies**: {hobbies}
**Interests**: {interests}
**Communication Style**: {profile.communication_style or 'natural'}
**Writing Tone**: {profile.writing_tone or 'conversational'}
**Frequently Discussed Topics**: {topics}
**Summary**: {profile.summary}

IMPORTANT RULES:
1. Write in the EXACT same style and tone as this person
2. Use similar vocabulary and sentence structure
3. Reference their interests and hobbies naturally when relevant
4. Keep the same level of formality they typically use
5. Be authentic — you ARE this person's digital representative
6. Do not break character or mention that you are an AI
7. If asked about personal preferences, answer based on the profile above"""


def generate_chat_response(
    profile: UserProfile,
    message: str,
    conversation_history: list[ChatMessage] | None = None,
    openai_api_key: str | None = None,
) -> str:
    """Generate a chat response in the user's style.

    Args:
        profile: The user's personality profile.
        message: The incoming message to respond to.
        conversation_history: Previous messages in the conversation.
        openai_api_key: Optional API key override.

    Returns:
        The generated response text.
    """
    api_key = openai_api_key or OPENAI_API_KEY
    client = OpenAI(api_key=api_key)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _build_system_prompt(profile)},
    ]

    if conversation_history:
        for msg in conversation_history:
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )

    return response.choices[0].message.content or ""


def generate_email_reply(
    profile: UserProfile,
    original_subject: str,
    original_body: str,
    sender_name: str = "",
    additional_context: str = "",
    openai_api_key: str | None = None,
) -> str:
    """Generate an email reply in the user's style.

    Args:
        profile: The user's personality profile.
        original_subject: Subject of the email being replied to.
        original_body: Body of the email being replied to.
        sender_name: Name of the person who sent the original email.
        additional_context: Any extra instructions for the reply.
        openai_api_key: Optional API key override.

    Returns:
        The generated email reply text.
    """
    api_key = openai_api_key or OPENAI_API_KEY
    client = OpenAI(api_key=api_key)

    system_prompt = _build_system_prompt(profile)
    system_prompt += "\n\nYou are now composing an EMAIL REPLY. Follow proper email etiquette while staying true to the personality profile."

    user_prompt = f"""Please write an email reply to the following email:

From: {sender_name or 'Someone'}
Subject: {original_subject}

{original_body}"""

    if additional_context:
        user_prompt += f"\n\nAdditional context for the reply: {additional_context}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    return response.choices[0].message.content or ""

"""Tests for the LLM responder module."""

from backend.llm.responder import _build_system_prompt
from backend.models.schemas import UserProfile


class TestBuildSystemPrompt:
    def _make_profile(self, **kwargs) -> UserProfile:
        defaults = {
            "email": "test@example.com",
            "name": "Test User",
            "personality_traits": ["friendly", "curious"],
            "hobbies": ["reading", "hiking"],
            "interests": ["technology", "science"],
            "communication_style": "casual and warm",
            "frequently_discussed_topics": ["AI", "travel"],
            "purchase_categories": ["books", "electronics"],
            "writing_tone": "friendly and informal",
            "summary": "A curious tech enthusiast who loves the outdoors.",
        }
        defaults.update(kwargs)
        return UserProfile(**defaults)

    def test_includes_personality_traits(self):
        profile = self._make_profile()
        prompt = _build_system_prompt(profile)
        assert "friendly" in prompt
        assert "curious" in prompt

    def test_includes_hobbies(self):
        profile = self._make_profile()
        prompt = _build_system_prompt(profile)
        assert "reading" in prompt
        assert "hiking" in prompt

    def test_includes_name(self):
        profile = self._make_profile(name="Alice")
        prompt = _build_system_prompt(profile)
        assert "Alice" in prompt

    def test_uses_email_when_no_name(self):
        profile = self._make_profile(name="")
        prompt = _build_system_prompt(profile)
        assert "test@example.com" in prompt

    def test_handles_empty_traits(self):
        profile = self._make_profile(personality_traits=[])
        prompt = _build_system_prompt(profile)
        assert "unknown" in prompt

    def test_includes_communication_style(self):
        profile = self._make_profile()
        prompt = _build_system_prompt(profile)
        assert "casual and warm" in prompt

    def test_includes_important_rules(self):
        profile = self._make_profile()
        prompt = _build_system_prompt(profile)
        assert "IMPORTANT RULES" in prompt
        assert "digital representative" in prompt

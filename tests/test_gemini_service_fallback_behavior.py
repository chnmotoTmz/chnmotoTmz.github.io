import sys
import os
import pytest
import requests

# Make sure 'src' package is importable
sys.path.insert(0, os.getcwd())


def test_generate_text_no_fallback_raises_when_custom_api_fails(monkeypatch):
    """If the custom LLM API fails and fallback is disabled, generate_text should raise RuntimeError."""
    def fail_post(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setenv('CUSTOM_LLM_FALLBACK_TO_CLAUDE', 'false')
    monkeypatch.setattr('requests.post', fail_post)

    from src.services.gemini_service import GeminiService

    gs = GeminiService()
    with pytest.raises(RuntimeError):
        gs.generate_text("hello world")


def test_generate_text_with_fallback_calls_claude(monkeypatch):
    """When fallback is enabled, the service should call Claude if the custom API fails."""
    def fail_post(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setenv('CUSTOM_LLM_FALLBACK_TO_CLAUDE', 'true')
    monkeypatch.setattr('requests.post', fail_post)

    class DummyClaude:
        def generate_text(self, prompt, max_tokens=None, temperature=None):
            return "claude response"

    # Replace ClaudeService factory with one that returns our dummy implementation
    monkeypatch.setattr('src.services.gemini_service.ClaudeService', lambda *a, **k: DummyClaude())

    from src.services.gemini_service import GeminiService

    gs = GeminiService()
    res = gs.generate_text("hello world")
    assert res == "claude response"

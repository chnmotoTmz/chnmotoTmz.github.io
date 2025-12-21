import sys
import os
import pytest

# Ensure imports work
sys.path.insert(0, os.getcwd())

class DummyGeminiClient:
    def __init__(self, cookies=None):
        self.cookies = cookies
    def generate_text(self, prompt):
        return "internal gemini response"


def test_internal_gemini_client_preferred(monkeypatch):
    # Set env cookies so Gemini client initializes
    monkeypatch.setenv('GEMINI_1PSID', 'abc')
    monkeypatch.setenv('GEMINI_1PSIDTS', 'def')

    # Replace gemini.Gemini with dummy constructor
    monkeypatch.setattr('src.services.gemini_service.Gemini', lambda cookies=None: DummyGeminiClient(cookies=cookies))

    # Make sure requests.post would fail if used (to ensure internal client was used)
    def fail_post(*args, **kwargs):
        raise RuntimeError("HTTP API should not be called when internal client is available")
    monkeypatch.setattr('requests.post', fail_post)

    from src.services.gemini_service import GeminiService
    gs = GeminiService()
    res = gs.generate_text("hello")
    assert res == "internal gemini response"

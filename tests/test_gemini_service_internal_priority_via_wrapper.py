import sys
import os
import pytest

# Ensure imports
sys.path.insert(0, os.getcwd())

class DummyGeminiClient:
    def __init__(self, cookies=None):
        self.cookies = cookies
    def generate_text(self, prompt):
        return "internal gemini response from wrapper"


def test_internal_gemini_client_initialized_from_wrapper_cookies(monkeypatch):
    # Simulate wrapper returning cookies
    def fake_fetch_cookies_from_wrapper(api_root, timeout=10):
        return {'__Secure-1PSID': 'XYZ', '__Secure-1PSIDTS': 'TS'}

    monkeypatch.setattr('src.services.gemini_service.fetch_cookies_from_wrapper', fake_fetch_cookies_from_wrapper)
    # Replace Gemini constructor
    monkeypatch.setattr('src.services.gemini_service.Gemini', lambda cookies=None: DummyGeminiClient(cookies=cookies))
    # Prevent HTTP POST from being used
    def fail_post(*args, **kwargs):
        raise RuntimeError("HTTP API should not be called when internal client is initialized from wrapper cookies")
    monkeypatch.setattr('requests.post', fail_post)

    from src.services.gemini_service import GeminiService
    gs = GeminiService()
    res = gs.generate_text("hello")
    assert res == "internal gemini response from wrapper"

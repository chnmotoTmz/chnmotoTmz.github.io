import os
import sys
# Ensure project root is on sys.path for imports in test environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import src.services.gemini_service as gs
import src.services.gemini_cookie_manager as gcm
from src.services.gemini_service import GeminiService

class DummyGemini:
    def __init__(self, *args, **kwargs):
        if kwargs.get('auto_cookies'):
            self.mode = 'auto'
        elif kwargs.get('cookies'):
            self.mode = 'cookies'
        else:
            self.mode = 'default'
    def generate_text(self, prompt):
        return 'ok'


def test_auto_cookies_taken(monkeypatch):
    monkeypatch.setenv('USE_PYTHON_GEMINI_API', 'true')
    monkeypatch.setattr(gs, 'Gemini', DummyGemini)

    svc = GeminiService()
    assert svc.gemini_client is not None
    assert getattr(svc.gemini_client, 'mode', None) == 'auto'


def test_auto_cookies_fails_then_wrapper(monkeypatch):
    class FailingGemini:
        def __init__(self, *args, **kwargs):
            if kwargs.get('auto_cookies'):
                raise RuntimeError('auto failed')
            if kwargs.get('cookies'):
                self.mode = 'cookies'

    monkeypatch.setenv('USE_PYTHON_GEMINI_API', 'true')
    monkeypatch.setattr(gs, 'Gemini', FailingGemini)
    monkeypatch.setattr(gcm, 'fetch_cookies_from_wrapper', lambda api_root: {'__Secure-1PSID': 'x', '__Secure-1PSIDTS': 'y'})

    svc = GeminiService()
    assert svc.gemini_client is not None
    assert getattr(svc.gemini_client, 'mode', None) == 'cookies'


def test_disable_python_gemini_api(monkeypatch):
    monkeypatch.setenv('USE_PYTHON_GEMINI_API', 'false')
    monkeypatch.setattr(gs, 'Gemini', DummyGemini)

    svc = GeminiService()
    assert svc.gemini_client is None

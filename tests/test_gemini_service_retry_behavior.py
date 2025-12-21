import os
import sys
import requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.services.gemini_service import GeminiService

class DummyResp:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data or {'answer': 'ok'}
    def json(self):
        return self._data


def test_retry_succeeds_after_timeout(monkeypatch):
    calls = {'n': 0}
    def fake_post(*a, **k):
        calls['n'] += 1
        if calls['n'] == 1:
            raise requests.ReadTimeout('timeout')
        return DummyResp(200, {'answer': 'ok'})
    monkeypatch.setattr('requests.post', fake_post)

    # ensure Claude fallback disabled to test retry behavior
    monkeypatch.setenv('CUSTOM_LLM_FALLBACK_TO_CLAUDE', 'false')

    svc = GeminiService()
    res = svc.generate_text('prompt text')
    assert res == 'ok'


def test_retries_exhausted_then_runtimeerror(monkeypatch):
    def fake_post(*a, **k):
        raise requests.ReadTimeout('timeout')
    monkeypatch.setattr('requests.post', fake_post)
    monkeypatch.setenv('CUSTOM_LLM_FALLBACK_TO_CLAUDE', 'false')
    # reduce retries to speed tests
    monkeypatch.setenv('CUSTOM_LLM_API_RETRIES', '1')

    svc = GeminiService()
    try:
        svc.generate_text('x')
        assert False, 'should have raised'
    except RuntimeError as e:
        assert 'custom API and Claude unavailable' in str(e)

import os
import sys
import json
import requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.services.gemini_service import GeminiService


def make_resp(status=500, text='error'):
    class R:
        status_code = status
        text = text
        def json(self):
            try:
                return json.loads(self.text)
            except Exception:
                return {}
    return R()


def test_custom_api_non_200_logged_and_fallback(monkeypatch, caplog):
    monkeypatch.setenv('CUSTOM_LLM_API_URL', 'http://localhost:3000/api/ask')
    monkeypatch.setenv('CUSTOM_LLM_FALLBACK_TO_CLAUDE', 'true')

    # make requests.post return 500 with body
    def fake_post(*a, **k):
        return make_resp(500, '{"error":"Timeout waiting for Gemini response"}')
    monkeypatch.setattr('requests.post', fake_post)

    # stub ClaudeService to return something
    class DummyClaude:
        def generate_text(self, prompt, **kwargs):
            return 'claude-reply'
    monkeypatch.setattr('src.services.gemini_service.ClaudeService', lambda *a, **k: DummyClaude())

    svc = GeminiService()

    with caplog.at_level('WARNING'):
        res = svc.generate_text('hi')
        assert res == 'claude-reply'
        # should have logged the body
        assert any('Timeout waiting for Gemini response' in m for m in caplog.messages)


def test_custom_api_200_no_text_logged(monkeypatch, caplog):
    monkeypatch.setenv('CUSTOM_LLM_API_URL', 'http://localhost:3000/api/ask')
    # 200 but no usable field
    def fake_post(*a, **k):
        return make_resp(200, '{}')
    monkeypatch.setattr('requests.post', fake_post)

    monkeypatch.setenv('CUSTOM_LLM_FALLBACK_TO_CLAUDE', 'false')
    svc = GeminiService()
    with caplog.at_level('WARNING'):
        try:
            svc.generate_text('hi')
        except RuntimeError as e:
            assert 'custom API and Claude unavailable' in str(e)
            assert any('Custom LLM API returned no usable text' in m for m in caplog.messages)

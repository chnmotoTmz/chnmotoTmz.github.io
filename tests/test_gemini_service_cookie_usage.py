import sys
import os
import pytest
import requests

# Ensure the workspace root is on sys.path so 'src' package is importable in CI/pytest runs
sys.path.insert(0, os.getcwd())

from types import SimpleNamespace


def make_response(status=200, json_data=None):
    r = SimpleNamespace()
    r.status_code = status
    r._json = json_data or {}
    def _json():
        return r._json
    r.json = _json
    return r


def test_generate_text_fetches_and_uses_cookies(monkeypatch):
    # Simulate GET /api/cookies returning cookie dict
    cookies_resp = make_response(json_data={
        'cookies': {
            'google.com': [
                {'name': '__Secure-1PSID', 'value': 'ABC123'},
            ]
        }
    })

    captured = {}

    def fake_get(url, timeout=None):
        captured['get_url'] = url
        return cookies_resp

    def fake_post(url, json=None, headers=None, timeout=None):
        captured['post_url'] = url
        captured['post_headers'] = headers
        # reply as the custom API would
        return make_response(json_data={'answer': {'text': 'hello from custom api'}})

    monkeypatch.setattr('requests.get', fake_get)
    monkeypatch.setattr('requests.post', fake_post)

    from src.services.gemini_service import GeminiService

    gs = GeminiService()
    res = gs.generate_text("test prompt")
    assert res == 'hello from custom api'
    assert 'get_url' in captured
    assert '/api/cookies' in captured['get_url']
    assert 'post_headers' in captured
    assert captured['post_headers'] and 'Cookie' in captured['post_headers']
    assert '__Secure-1PSID=ABC123' in captured['post_headers']['Cookie']

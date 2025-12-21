import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests
from unittest.mock import MagicMock
from src.services.gemini_service import GeminiService


def test_generate_text_includes_new_chat(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured['url'] = url
        captured['json'] = json
        class Resp:
            status_code = 200
            def json(self):
                return {'answer': {'text': 'ok'}}
        return Resp()

    monkeypatch.setattr(requests, 'post', fake_post)

    svc = GeminiService()
    res = svc.generate_text('hello', new_chat=True, mode='fast')

    assert res == 'ok'
    assert 'json' in captured
    assert captured['json'].get('new_chat') is True
    assert captured['json'].get('mode') == 'fast'

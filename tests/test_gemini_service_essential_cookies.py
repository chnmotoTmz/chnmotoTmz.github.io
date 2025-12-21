import sys
import os
import pytest

sys.path.insert(0, os.getcwd())

from types import SimpleNamespace


def test_gemini_service_passes_only_essential_cookies(monkeypatch):
    # Simulate fetch_cookies_from_wrapper returning many cookies
    def fake_fetch(api_root, timeout=10):
        return {
            '__Secure-1PSID': 'A',
            '__Secure-1PSIDTS': 'B',
            '__Secure-1PSIDCC': 'C',
            'OTHER': 'X'
        }
    monkeypatch.setattr('src.services.gemini_service.fetch_cookies_from_wrapper', fake_fetch)

    captured = {}
    def dummy_gemini_constructor(cookies=None):
        captured['cookies'] = cookies
        class Dummy:
            def generate_text(self, prompt):
                return 'ok'
        return Dummy()

    monkeypatch.setattr('src.services.gemini_service.Gemini', dummy_gemini_constructor)

    from src.services.gemini_service import GeminiService
    gs = GeminiService()
    res = gs.generate_text('hello')
    assert res == 'ok'
    assert set(captured['cookies'].keys()) == {'__Secure-1PSID','__Secure-1PSIDTS','__Secure-1PSIDCC'}
    assert 'OTHER' not in captured['cookies']

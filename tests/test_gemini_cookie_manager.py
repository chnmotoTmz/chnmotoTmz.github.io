import sys
import os
import pytest

sys.path.insert(0, os.getcwd())

from src.services.gemini_cookie_manager import fetch_cookies_from_wrapper

class DummyResp:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status
    def json(self):
        return self._json


def test_fetch_cookies_from_wrapper_converts_and_returns_essential(monkeypatch):
    sample = {
        'success': True,
        'cookies': {
            'google.com': [
                {'name': '__Secure-1PSID', 'value': 'A'},
                {'name': '__Secure-1PSIDTS', 'value': 'B'},
                {'name': '__Secure-1PSIDCC', 'value': 'C'},
                {'name': 'OTHER', 'value': 'X'}
            ]
        }
    }

    def fake_get(url, timeout=None):
        return DummyResp(sample)

    monkeypatch.setattr('requests.get', fake_get)

    cookies = fetch_cookies_from_wrapper('http://localhost:3000')
    assert cookies == {
        '__Secure-1PSID': 'A',
        '__Secure-1PSIDTS': 'B',
        '__Secure-1PSIDCC': 'C'
    }


def test_fetch_cookies_partial_sets_returns_partial_and_logs(monkeypatch, caplog):
    sample = {
        'success': True,
        'cookies': {
            'google.com': [
                {'name': '__Secure-1PSID', 'value': 'A'},
            ]
        }
    }
    def fake_get(url, timeout=None):
        return DummyResp(sample)
    monkeypatch.setattr('requests.get', fake_get)

    caplog.set_level("WARNING")
    cookies = fetch_cookies_from_wrapper('http://localhost:3000')
    assert cookies == {'__Secure-1PSID': 'A'}
    assert any('Partial cookie set' in m.message for m in caplog.records)

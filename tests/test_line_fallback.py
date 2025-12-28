import pytest
from linebot.exceptions import LineBotApiError
from src.services.line_service import LineService

def test_send_message_rate_limit_triggers_fallback(monkeypatch):
    svc = LineService(channel_access_token=None)

    # Monkeypatch the LineBotApiError used in the service to a simple test-friendly class
    class _FakeLBError(Exception):
        def __init__(self, status_code=429, error=None):
            self.status_code = status_code
            self.error = error or {}
    monkeypatch.setattr('src.services.line_service.LineBotApiError', _FakeLBError)

    # Make push_message raise the fake LineBotApiError
    def fake_push(user_id, message):
        raise _FakeLBError(429, {'message': 'You have reached your monthly limit.'})

    svc.line_bot_api.push_message = fake_push

    called = {}
    def fake_email(recipient, subject, body):
        called['recipient'] = recipient
        called['subject'] = subject
        called['body'] = body
        return True

    monkeypatch.setattr(svc, '_send_email_fallback', fake_email)

    result = svc.send_message('U123', 'Article published!')

    assert result is False
    assert called['recipient']  # fallback attempted
    assert 'Article published' in called['body']

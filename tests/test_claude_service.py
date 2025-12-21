import os
import pytest
from src.services.claude_service import ClaudeService

class DummyResp:
    def __init__(self, status_code, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError('no json')
        return self._json


def test_alias_mapping_applied(monkeypatch):
    os.environ['CLAUDE_MODEL_ALIASES'] = 'claude-haiku-4:claude-3-5-sonnet-20240620'

    captured = {}
    def fake_post(url, json=None, headers=None, timeout=None):
        captured['json'] = json
        return DummyResp(200, {'output': 'ok'})

    monkeypatch.setattr('requests.post', fake_post)
    svc = ClaudeService(model='claude-haiku-4')
    res = svc.generate_text('hello', max_tokens=10)
    assert res == 'ok'
    assert captured['json']['model'] == 'claude-3-5-sonnet-20240620'


def test_model_not_found_fallbacks(monkeypatch):
    os.environ.pop('CLAUDE_MODEL_ALIASES', None)
    os.environ['CLAUDE_FALLBACK_MODELS'] = 'alt1,alt2'

    # sequence: first 404 with model-not-found, second 404, third 200
    calls = []
    responses = [
        DummyResp(404, {'type': 'error', 'error': {'type': 'not_found_error', 'message': 'model: missing-model'}, 'request_id': 'req_123'}, text='model: missing-model'),
        DummyResp(404, None, text='not found'),
        DummyResp(200, {'completion': 'fallback ok'})
    ]

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        return responses[len(calls)-1]

    monkeypatch.setattr('requests.post', fake_post)
    svc = ClaudeService(model='missing-model')
    res = svc.generate_text('hi', max_tokens=10)
    assert res == 'fallback ok'
    # ensure we tried fallback models alt1 and alt2 after initial
    models_tried = [call['model'] for call in calls]
    assert 'alt1' in models_tried and 'alt2' in models_tried


def test_all_fallbacks_fail_raises(monkeypatch):
    os.environ['CLAUDE_FALLBACK_MODELS'] = 'a,b'
    rsp = DummyResp(404, {'type': 'error', 'error': {'type': 'not_found_error', 'message': 'model: missing-model'}, 'request_id': 'req_999'}, text='model: missing-model')

    def fake_post(url, json=None, headers=None, timeout=None):
        return rsp

    monkeypatch.setattr('requests.post', fake_post)
    svc = ClaudeService(model='missing-model')
    with pytest.raises(RuntimeError) as ei:
        svc.generate_text('x')
    assert 'req_999' in str(ei.value)

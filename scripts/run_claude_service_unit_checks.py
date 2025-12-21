import os
import sys
from types import SimpleNamespace

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


def run_alias_mapping_check():
    os.environ['CLAUDE_MODEL_ALIASES'] = 'claude-haiku-4:claude-3-5-sonnet-20240620'
    captured = {}
    def fake_post(url, json=None, headers=None, timeout=None):
        captured['json'] = json
        return DummyResp(200, {'output': 'ok'})
    import requests
    real_post = requests.post
    requests.post = fake_post
    try:
        svc = ClaudeService(model='claude-haiku-4')
        res = svc.generate_text('hello', max_tokens=10)
        assert res == 'ok'
        assert captured['json']['model'] == 'claude-3-5-sonnet-20240620'
        print('alias_mapping: PASS')
    finally:
        requests.post = real_post


def run_model_not_found_fallbacks_check():
    os.environ.pop('CLAUDE_MODEL_ALIASES', None)
    os.environ['CLAUDE_FALLBACK_MODELS'] = 'alt1,alt2'
    calls = []
    responses = [
        DummyResp(404, {'type': 'error', 'error': {'type': 'not_found_error', 'message': 'model: missing-model'}, 'request_id': 'req_123'}, text='model: missing-model'),
        DummyResp(404, None, text='not found'),
        DummyResp(200, {'completion': 'fallback ok'})
    ]
    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        return responses[len(calls)-1]
    import requests
    real_post = requests.post
    requests.post = fake_post
    try:
        svc = ClaudeService(model='missing-model')
        res = svc.generate_text('hi', max_tokens=10)
        assert res == 'fallback ok'
        models_tried = [call['model'] for call in calls]
        assert 'alt1' in models_tried and 'alt2' in models_tried
        print('model_not_found_fallbacks: PASS')
    finally:
        requests.post = real_post


def run_all_fallbacks_fail_check():
    os.environ['CLAUDE_FALLBACK_MODELS'] = 'a,b'
    rsp = DummyResp(404, {'type': 'error', 'error': {'type': 'not_found_error', 'message': 'model: missing-model'}, 'request_id': 'req_999'}, text='model: missing-model')
    def fake_post(url, json=None, headers=None, timeout=None):
        return rsp
    import requests
    real_post = requests.post
    requests.post = fake_post
    try:
        svc = ClaudeService(model='missing-model')
        try:
            svc.generate_text('x')
            print('all_fallbacks_fail: FAIL (no exception)')
        except RuntimeError as e:
            if 'req_999' in str(e):
                print('all_fallbacks_fail: PASS')
            else:
                print('all_fallbacks_fail: FAIL (wrong error)')
    finally:
        requests.post = real_post


if __name__ == '__main__':
    run_alias_mapping_check()
    run_model_not_found_fallbacks_check()
    run_all_fallbacks_fail_check()

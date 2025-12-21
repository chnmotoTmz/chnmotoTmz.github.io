import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests
from unittest.mock import MagicMock
from src.services.thumbnail_generator_service import ThumbnailGeneratorService


def test_generate_via_custom_api_includes_mode_and_new_chat(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured['url'] = url
        captured['json'] = json
        class Resp:
            status_code = 200
            def json(self):
                return {'answer': {'images': [{'src': 'http://example.com/img.png'}]}}
        return Resp()

    monkeypatch.setattr(requests, 'post', fake_post)

    svc = ThumbnailGeneratorService()
    # Call with new_chat=True and verify payload contains mode=image and new_chat
    result = svc._generate_via_custom_api('a prompt', 'http://localhost:3000/api/ask', new_chat=True)

    assert captured['json'].get('mode') == 'image'
    assert captured['json'].get('new_chat') is True
    # Default behavior is to wait for browser download; since LOCAL_THUMBNAIL_DIR is not set, result will be None
    assert result is None

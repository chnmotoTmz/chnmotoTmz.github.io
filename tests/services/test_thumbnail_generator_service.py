import os
import sys
from pathlib import Path

# ensure repo src is importable when running tests directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import time
import tempfile
import base64
import threading

import pytest
import requests

from src.services.thumbnail_generator_service import ThumbnailGeneratorService


def is_api_up():
    try:
        resp = requests.post('http://localhost:3000/api/ask', json={'prompt': 'test'}, timeout=60)
        return resp.status_code == 200
    except:
        return False


class DummyMagichour:
    def generate_image(self, prompt):
        return {'images': [{'url': 'file:///tmp/dummy.png'}]}


class MockImgur:
    def __init__(self):
        self.uploaded = []

    def upload_image(self, path):
        self.uploaded.append(path)
        return {'success': True, 'link': 'https://i.imgur.com/mock.png'}


def make_1x1_png_base64():
    # A tiny 1x1 transparent PNG base64
    return (
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQI12NgYAAAAAMA'  # noqa: E501
        'ASsJTYQAAAAASUVORK5CYII='
    )


def test_custom_api_returns_base64(tmp_path, monkeypatch):
    if not is_api_up():
        pytest.skip('Custom thumbnail API not available on localhost:3000')

    temp_dir = tmp_path / "downloads"
    temp_dir.mkdir()

    monkeypatch.setenv('LOCAL_THUMBNAIL_DIR', str(temp_dir))
    monkeypatch.setenv('CUSTOM_THUMBNAIL_API_URL', 'http://localhost:3000/api/ask')

    # Use real API calls - no mocking
    imgur = MockImgur()
    svc = ThumbnailGeneratorService(magichour_service=DummyMagichour(), imgur_service=imgur)

    result = svc._generate_via_custom_api('A simple test image of a cat', 'http://localhost:3000/api/ask')

    assert result.startswith('https://i.imgur.com/')
    # Ensure the uploaded path was a temp file and removed
    assert len(imgur.uploaded) == 1
    assert 'thumb_' in imgur.uploaded[0]


def test_custom_api_polling_fallback(tmp_path, monkeypatch):
    # This test is no longer relevant with the new 3-step logic
    # The new logic always expects a JSON response with images
    pass


def test_custom_api_src_needs_download(tmp_path, monkeypatch):
    if not is_api_up():
        pytest.skip('Custom thumbnail API not available on localhost:3000')

    temp_dir = tmp_path / "downloads"
    temp_dir.mkdir()

    monkeypatch.setenv('LOCAL_THUMBNAIL_DIR', str(temp_dir))
    monkeypatch.setenv('CUSTOM_THUMBNAIL_API_URL', 'http://localhost:3000/api/ask')

    # Use real API calls - no mocking
    imgur = MockImgur()
    svc = ThumbnailGeneratorService(magichour_service=DummyMagichour(), imgur_service=imgur)

    result = svc._generate_via_custom_api('A beautiful sunset over mountains', 'http://localhost:3000/api/ask')

    assert result.startswith('https://i.imgur.com/')
    assert len(imgur.uploaded) == 1


def test_generate_and_upload_uses_default_custom_api_when_env_not_set(monkeypatch):
    # Ensure CUSTOM_THUMBNAIL_API_URL is not set so default is used
    monkeypatch.delenv('CUSTOM_THUMBNAIL_API_URL', raising=False)

    captured = {}
    def fake_generate_via_custom_api(self, prompt, api_url, new_chat=False):
        captured['api_url'] = api_url
        return 'https://i.imgur.com/mock.png'

    monkeypatch.setattr(ThumbnailGeneratorService, '_generate_via_custom_api', fake_generate_via_custom_api)

    imgur = MockImgur()
    svc = ThumbnailGeneratorService(magichour_service=DummyMagichour(), imgur_service=imgur)

    result = svc.generate_and_upload('Test prompt for default API')

    assert result == 'https://i.imgur.com/mock.png'
    # Verify default API URL is used
    assert captured.get('api_url') == 'http://localhost:3000/api/ask'

import os
import sys
from pathlib import Path
# ensure repo src is importable when running tests directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import time
import tempfile
import base64
import json
import pytest
from types import SimpleNamespace

from src.services.thumbnail_generator_service import ThumbnailGeneratorService


class MockImgur:
    def __init__(self):
        self.uploaded = []

    def upload_image(self, path):
        self.uploaded.append(path)
        return {'success': True, 'link': 'https://i.imgur.com/mock.png'}


class DummyMagichour:
    def generate_image(self, prompt):
        return {'images': [{'url': 'file:///tmp/dummy.png'}]}


def make_1x1_png_base64():
    return (
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQI12NgYAAAAAMA'
        'ASsJTYQAAAAASUVORK5CYII='
    )


def test_generate_from_data_uri(monkeypatch, tmp_path):
    # Legacy path: enable old Python-side decoding via env
    monkeypatch.setenv('ENABLE_CUSTOM_API_IMAGE_DOWNLOADS', 'true')

    # Mock API response to return a data URI
    data_uri = f"data:image/png;base64,{make_1x1_png_base64()}"

    def fake_post(url, json=None, timeout=None, headers=None):
        return SimpleNamespace(status_code=200, json=lambda: {'answer': {'images': [{'src': data_uri}]}})

    monkeypatch.setattr('requests.post', fake_post)

    imgur = MockImgur()
    svc = ThumbnailGeneratorService(magichour_service=DummyMagichour(), imgur_service=imgur)

    # ensure temp folder exists
    os.makedirs(svc.temp_folder, exist_ok=True)

    result = svc._generate_via_custom_api('prompt', 'http://localhost:3000/api/ask')

    assert result == 'https://i.imgur.com/mock.png'
    assert len(imgur.uploaded) == 1
    # uploaded file should be removed from temp_folder (since service deletes temp files it created)


def test_default_ignores_image_metadata(monkeypatch, tmp_path, caplog):
    # Default behavior: do NOT perform downloads/decoding
    # Mock API response to return a data URI
    data_uri = f"data:image/png;base64,{make_1x1_png_base64()}"

    def fake_post(url, json=None, timeout=None, headers=None):
        return SimpleNamespace(status_code=200, json=lambda: {'answer': {'images': [{'src': data_uri}]}})

    monkeypatch.setattr('requests.post', fake_post)

    imgur = MockImgur()
    svc = ThumbnailGeneratorService(magichour_service=DummyMagichour(), imgur_service=imgur)

    # ensure temp folder exists
    os.makedirs(svc.temp_folder, exist_ok=True)

    result = svc._generate_via_custom_api('prompt', 'http://localhost:3000/api/ask')

    # Since LOCAL_THUMBNAIL_DIR is not set and default behavior is to ignore images, result should be None
    assert result is None
    assert any('Custom API returned image metadata' in rec.getMessage() for rec in caplog.records)


def test_generate_from_http_src(monkeypatch, tmp_path):
    # Legacy path enabled
    monkeypatch.setenv('ENABLE_CUSTOM_API_IMAGE_DOWNLOADS', 'true')

    image_bytes = b'PNGDATA'

    def fake_post(url, json=None, timeout=None, headers=None):
        return SimpleNamespace(status_code=200, json=lambda: {'answer': {'images': [{'src': 'https://example.com/test.png'}]}})

    class FakeResp:
        def __init__(self):
            self.status_code = 200
            self.content = image_bytes
            self.headers = {'Content-Type': 'image/png'}

    call_headers = []

    def fake_get(url, timeout=None, headers=None):
        # first call returns 403, second returns 200
        call_headers.append(headers)
        if len(call_headers) == 1:
            return SimpleNamespace(status_code=403)
        return FakeResp()

    monkeypatch.setattr('requests.post', fake_post)
    monkeypatch.setattr('requests.get', fake_get)

    imgur = MockImgur()
    svc = ThumbnailGeneratorService(magichour_service=DummyMagichour(), imgur_service=imgur)

    os.makedirs(svc.temp_folder, exist_ok=True)

    result = svc._generate_via_custom_api('prompt', 'http://localhost:3000/api/ask')

    assert result == 'https://i.imgur.com/mock.png'
    assert len(imgur.uploaded) == 1
    # The second call should have headers set
    assert call_headers[1] is not None
    assert 'User-Agent' in call_headers[1]
    assert 'Referer' in call_headers[1]


def test_http_download_permanent_403(monkeypatch, tmp_path, caplog):
    # Legacy path enabled to assert previous 403 behavior
    monkeypatch.setenv('ENABLE_CUSTOM_API_IMAGE_DOWNLOADS', 'true')

    def fake_post(url, json=None, timeout=None, headers=None):
        return SimpleNamespace(status_code=200, json=lambda: {'answer': {'images': [{'src': 'https://example.com/test.png'}]}})

    def fake_get(url, timeout=None, headers=None):
        return SimpleNamespace(status_code=403)

    monkeypatch.setattr('requests.post', fake_post)
    monkeypatch.setattr('requests.get', fake_get)

    imgur = MockImgur()
    svc = ThumbnailGeneratorService(magichour_service=DummyMagichour(), imgur_service=imgur)

    os.makedirs(svc.temp_folder, exist_ok=True)

    result = svc._generate_via_custom_api('prompt', 'http://localhost:3000/api/ask')

    assert result is None
    # Ensure we logged a helpful message about 403
    assert any('403' in rec.getMessage() or 'ホットリンク' in rec.getMessage() for rec in caplog.records)

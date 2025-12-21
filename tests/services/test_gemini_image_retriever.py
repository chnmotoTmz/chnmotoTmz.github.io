import os
import sys
import tempfile
import json
from pathlib import Path

# Ensure repo src is importable when running tests directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import requests

from src.services.gemini_image_retriever import GeminiImageRetriever

class DummyResp:
    def __init__(self, status_code=200, json_data=None, content=b''):
        self.status_code = status_code
        self._json = json_data or {}
        self.content = content

    def json(self):
        return self._json


def test_retrieve_image_from_base64(tmp_path, monkeypatch):
    temp_dir = tmp_path / "downloads"
    temp_dir.mkdir()

    base64_png = 'data:image/png;base64,' + (
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQI12NgYAAAAAMA'
        'ASsJTYQAAAAASUVORK5CYII='
    )

    json_body = {"answer": {"images": [{"src": base64_png}]}}

    def fake_post(url, json=None, timeout=None, headers=None):
        return DummyResp(200, json_data=json_body)

    monkeypatch.setattr(requests, 'post', fake_post)

    retriever = GeminiImageRetriever(api_url='http://localhost:3000/api/ask', local_thumbnail_dir=str(temp_dir))
    path = retriever.retrieve_image('test prompt')

    assert path is not None
    assert Path(path).exists()


def test_retrieve_image_by_http(tmp_path, monkeypatch):
    temp_dir = tmp_path / "downloads"
    temp_dir.mkdir()

    remote_url = 'http://example.com/test.png'
    json_body = {"answer": {"images": [{"src": remote_url}]}}

    def fake_post(url, json=None, timeout=None, headers=None):
        return DummyResp(200, json_data=json_body)

    def fake_get(url, timeout=None):
        return DummyResp(200, content=b'PNGDATA')

    monkeypatch.setattr(requests, 'post', fake_post)
    monkeypatch.setattr(requests, 'get', fake_get)

    retriever = GeminiImageRetriever(api_url='http://localhost:3000/api/ask', local_thumbnail_dir=str(temp_dir))
    path = retriever.retrieve_image('test prompt')

    assert path is not None
    assert Path(path).exists()
    assert Path(path).read_bytes() == b'PNGDATA'


def test_no_images_returns_none(monkeypatch):
    def fake_post(url, json=None, timeout=None, headers=None):
        return DummyResp(200, json_data={"answer": {"images": []}})

    monkeypatch.setattr(requests, 'post', fake_post)

    retriever = GeminiImageRetriever(api_url='http://localhost:3000/api/ask')
    assert retriever.retrieve_image('test prompt') is None

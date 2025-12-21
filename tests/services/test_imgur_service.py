import os
import tempfile
import base64
import requests
import json
import pytest
from pathlib import Path
import sys

# ensure repo src is importable when running tests directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services.imgur_service import ImgurService


class MockResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {"success": True, "data": {"link": "https://i.imgur.com/test.png"}}
        self.text = text
        self.headers = {"content-type": "application/json"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)

    def json(self):
        return self._json_data


def make_1x1_png(path: Path):
    b64 = (
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQI12NgYAAAAAMA'
        'ASsJTYQAAAAASUVORK5CYII='
    )
    data = base64.b64decode(b64)
    with open(path, "wb") as f:
        f.write(data)


def test_upload_image_with_mock(monkeypatch, tmp_path):
    tmp_file = tmp_path / "test.png"
    make_1x1_png(tmp_file)

    # Create a session with mocked post
    session = requests.Session()

    def fake_post(url, headers=None, files=None, data=None, timeout=None):
        assert url == "https://api.imgur.com/3/image"
        # basic header check
        assert headers is not None
        return MockResponse()

    monkeypatch.setattr(session, "post", fake_post)

    service = ImgurService(client_id="fake-client", access_token=None, session=session)
    result = service.upload_image(str(tmp_file), title="t1", description="desc")

    assert result.get("success") is True
    assert result.get("link") == "https://i.imgur.com/test.png"


def test_download_and_upload_flow(monkeypatch, tmp_path):
    # Attempt to download a public placeholder image; skip if network unavailable
    url = "https://via.placeholder.com/150"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            pytest.skip("Unable to fetch placeholder image")
    except Exception:
        pytest.skip("Network unavailable for downloading test image")

    tmp_file = tmp_path / "downloaded.png"
    with open(tmp_file, "wb") as f:
        f.write(resp.content)

    # Mock ImgurService session.post to simulate Imgur
    session = requests.Session()

    def fake_post(url, headers=None, files=None, data=None, timeout=None):
        # ensure the uploaded file exists in the files mapping
        assert files and "image" in files
        return MockResponse()

    monkeypatch.setattr(session, "post", fake_post)

    service = ImgurService(client_id="fake-client", session=session)
    result = service.upload_image(str(tmp_file))

    assert result.get("success") is True
    assert result.get("link").startswith("https://i.imgur.com/")


def test_integration_upload_skipped_if_no_creds(tmp_path):
    # Create temp image
    tmp_file = tmp_path / "local.png"
    make_1x1_png(tmp_file)

    if not (os.getenv("IMGUR_CLIENT_ID") or os.getenv("IMGUR_ACCESS_TOKEN")):
        pytest.skip("Imgur credentials not available for integration test")

    # With real creds, run the integration test (may incur network and API usage)
    service = ImgurService()
    result = service.upload_image(str(tmp_file))
    assert result.get("success") is True
    assert result.get("link")

import os
import types
import json
from src.tasks.hatena_publisher_task import HatenaPublisherTask

class DummyResp:
    def __init__(self, status_code=201, text="<entry></entry>"):
        self.status_code = status_code
        self.text = text


def test_local_image_uploads_and_publish(monkeypatch, tmp_path):
    # Prepare a fake BlogPost in DB-like structure
    # Create a temp image file
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xd9")

    # Create a fake post object
    class FakePost:
        content = f"<p>Intro</p><div><img src='file://{str(img_file)}' alt='pic' /></div>"
        title = "T"

    # Monkeypatch DB session query to return our FakePost and a simple Blog object
    class FakeQuery:
        def get(self, pid):
            return FakePost()
        def filter_by(self, **kwargs):
            class _First:
                def first(self):
                    # minimal Blog object with fields used by task
                    return types.SimpleNamespace(hatena_id='hid', hatena_blog_id=kwargs.get('hatena_blog_id', 'x'), api_key='apikey')
            return _First()

    monkeypatch.setattr('src.tasks.hatena_publisher_task.db', types.SimpleNamespace(session=types.SimpleNamespace(query=lambda *a, **k: FakeQuery())))

    # Monkeypatch ImgurService.upload_image to simulate success
    def fake_upload(p, title='', description='', privacy='hidden'):
        return {'success': True, 'link': 'https://img.example/test.jpg'}
    monkeypatch.setattr('src.tasks.hatena_publisher_task.ImgurService.upload_image', fake_upload)

    # Monkeypatch HatenaService._post_to_hatena to capture xml and return success
    captured = {}
    def fake_post(self, xml_data):
        captured['xml'] = xml_data
        return DummyResp(201, '<entry xmlns="http://www.w3.org/2005/Atom"><id>tag:sample-123</id><link rel="alternate" href="https://example.com/entry/1"/></entry>')
    monkeypatch.setattr('src.tasks.hatena_publisher_task.HatenaService._post_to_hatena', fake_post)

    task = HatenaPublisherTask({})
    inputs = {'blog': {'hatena_blog_id': 'x'}, 'post_id': 1}

    out = task.execute(inputs)

    # Ensure the content sent to Hatena has image URL replaced
    assert 'https://img.example/test.jpg' in captured['xml']
    assert out['hatena_entry']['url'].startswith('https://')

import os
import types
from src.tasks.hatena_publisher_task import HatenaPublisherTask
from src.database import BlogPost

def test_hatena_publisher_injects_thumbnail(monkeypatch, tmp_path):
    # Setup inputs
    img_file = tmp_path / "thumb.jpg"
    img_file.write_bytes(b"fake image data")
    
    inputs = {
        "blog": {"hatena_blog_id": "test.blog"},
        "post_id": 1,
        "thumbnail_path": str(img_file)
    }

    # Mock DB
    class FakePost:
        title = "Test Post"
        content = "Original Content"
    
    fake_post = FakePost()

    class FakeQuery:
        def get(self, pid):
            return fake_post
        def filter_by(self, **kwargs):
            return types.SimpleNamespace(first=lambda: types.SimpleNamespace(hatena_id='h', hatena_blog_id='b', api_key='k'))
    
    db_mock = types.SimpleNamespace(session=types.SimpleNamespace(
        query=lambda *a, **k: FakeQuery(),
        commit=lambda: None
    ))
    monkeypatch.setattr("src.tasks.hatena_publisher_task.db", db_mock)

    # Mock Imgur
    class FakeImgur:
        def upload_image(self, p):
            return {"success": True, "link": "https://imgur.com/uploaded.jpg"}
    monkeypatch.setattr("src.tasks.hatena_publisher_task.ImgurService", FakeImgur)

    # Mock HatenaService
    published_content = []
    class FakeHatenaService:
        def __init__(self, blog_config): pass
        def publish_article(self, title, content, **kwargs):
            published_content.append(content)
            return {"url": "http://hatena/entry/1"}
    monkeypatch.setattr("src.tasks.hatena_publisher_task.HatenaService", FakeHatenaService)

    # Execute
    task = HatenaPublisherTask({})
    task.execute(inputs)

    # Verify
    assert len(published_content) == 1
    content = published_content[0]
    
    # Check if thumbnail was injected
    assert "![Thumbnail](https://imgur.com/uploaded.jpg)" in content
    # Check if original content is preserved
    assert "Original Content" in content
    # Check TOC
    assert "[:contents]" in content
    
    # Check if DB post content was updated
    assert "![Thumbnail](https://imgur.com/uploaded.jpg)" in fake_post.content

def test_hatena_publisher_respects_existing_thumbnail(monkeypatch):
    # If content already has the thumbnail, don't duplicate
    inputs = {
        "blog": {"hatena_blog_id": "test.blog"},
        "post_id": 1,
        "thumbnail_path": "https://imgur.com/existing.jpg"
    }

    class FakePost:
        title = "Test Post"
        content = "![Thumbnail](https://imgur.com/existing.jpg)\n\nOriginal Content"
    
    fake_post = FakePost()

    # Mocks (simplified)
    db_mock = types.SimpleNamespace(session=types.SimpleNamespace(
        query=lambda *a, **k: types.SimpleNamespace(get=lambda x: fake_post, filter_by=lambda **kw: types.SimpleNamespace(first=lambda: types.SimpleNamespace(hatena_id='h', hatena_blog_id='b', api_key='k'))),
        commit=lambda: None
    ))
    monkeypatch.setattr("src.tasks.hatena_publisher_task.db", db_mock)
    monkeypatch.setattr("src.tasks.hatena_publisher_task.ImgurService", lambda: None) # Should not be called
    
    captured = []
    class FakeHatenaService:
        def __init__(self, blog_config): pass
        def publish_article(self, title, content, **kwargs):
            captured.append(content)
            return {"url": "http://hatena/entry/1"}
    monkeypatch.setattr("src.tasks.hatena_publisher_task.HatenaService", FakeHatenaService)

    task = HatenaPublisherTask({})
    task.execute(inputs)

    content = captured[0]
    # Should appear only once
    assert content.count("![Thumbnail](https://imgur.com/existing.jpg)") == 1

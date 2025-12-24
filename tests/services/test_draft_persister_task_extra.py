import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from src.tasks.draft_persister_task import DraftPersisterTask
from src.app_factory import create_app

app = create_app()

@pytest.fixture(scope='module')
def app_context():
    with app.app_context():
        yield


def test_persist_with_yaml_style_blog_and_line_user(app_context):
    task = DraftPersisterTask(config={})
    inputs = {
        'blog': {
            'hatena_blog_id': 'test.seed.blog',
            'blog_name': 'Test Seed Blog',
            'hatena_id': 'testseed',
            'hatena_api_key': 'seedkey'
        },
        'user': {
            'line_user_id': 'pytest-user-1',
            'display_name': 'PyTest User'
        },
        'title': 'PyTest Title',
        'content': '<p>content</p>',
        'message_ids': []
    }
    res = task.execute(inputs)
    assert isinstance(res, dict)
    assert res.get('post_id') is not None


def test_skip_when_blog_missing_identifiers(app_context):
    task = DraftPersisterTask(config={})
    inputs = {
        'blog': {'blog_name': 'No ID Blog'},
        'user': {'line_user_id': 'pytest-user-2'},
        'title': 'Title',
        'content': 'Content',
        'message_ids': []
    }
    res = task.execute(inputs)
    assert res == {'post_id': None}

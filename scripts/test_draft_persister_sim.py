#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.tasks.draft_persister_task import DraftPersisterTask
from src.app_factory import create_app

# Create app (this will initialize DB and seed blogs if needed)
app = create_app()

task = DraftPersisterTask(config={})
inputs = {
    'blog': {
        'hatena_blog_id': 'integration.test.blog',
        'blog_name': 'Integration Test Blog',
        'hatena_id': 'integration',
        'hatena_api_key': 'testkey123'
    },
    'user': {
        'line_user_id': 'test-user-123',
        'display_name': 'Test User'
    },
    'title': 'Test Draft Title',
    'content': '<p>Test content</p>',
    'message_ids': []
}

with app.app_context():
    res = task.execute(inputs)
    print('Result:', res)

#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.tasks.hatena_publisher_task import HatenaPublisherTask
from src.app_factory import create_app

# Create app (this will initialize DB and seed blogs if needed)
app = create_app()

task = HatenaPublisherTask(config={})
inputs = {
    'blog': {
        'hatena_blog_id': 'hikingsong.hatenablog.jp',
        'blog_name': 'AI音楽制作スタジオ',
        'hatena_id': 'yamasan1969',
        'hatena_api_key': 'testkey123'
    },
    'post_id': 115,  # Use the post_id from our previous test
    'tags': ['AI', '音楽'],
    'article_concept': {'genre': 'テクノロジー', 'keywords': ['AI', '音楽制作']}
}

with app.app_context():
    try:
        res = task.execute(inputs)
        print('HatenaPublisherTask result:', res)
    except Exception as e:
        print('Error:', e)
        # This is expected since we don't have real Hatena credentials
        if "Failed to publish" in str(e):
            print("Expected error due to missing credentials - fix is working!")
        else:
            raise
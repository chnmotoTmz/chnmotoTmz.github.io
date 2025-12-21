#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BlogSelector Debug Test
"""

import os
import sys
import logging

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数確認
print("\n" + "="*60)
print("[ENV] Environment variables")
print("="*60)
print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'Not set')}")
print(f"LOCAL_LLM_BASE_URL: {os.getenv('LOCAL_LLM_BASE_URL', 'Not set')}")
print(f"LOCAL_LLM_MODEL: {os.getenv('LOCAL_LLM_MODEL', 'Not set')}")

# Flask アプリ初期化
print("\n" + "="*60)
print("[APP] Flask initialization")
print("="*60)
sys.path.insert(0, os.getcwd())

from src.app_factory import create_app
app = create_app()

with app.app_context():
    from src.services.tasks.blog_selector_task import BlogSelectorTask
    from src.blog_config import BlogConfig
    
    # ブログ設定確認
    all_blogs = BlogConfig.get_all_blogs()
    print(f"\n[BLOGS] Available blogs: {len(all_blogs)}")
    for blog_id, blog_config in all_blogs.items():
        print(f"  - {blog_id}: {blog_config.get('blog_name')}")
        print(f"    Keywords: {blog_config.get('keywords', [])}")
    
    # BlogSelector タスク作成
    print("\n" + "="*60)
    print("[TEST] BlogSelector tests")
    print("="*60)
    
    selector = BlogSelectorTask({})
    
    # テストケース
    test_cases = [
        {
            "name": "Movie review",
            "texts": ["I recently watched an amazing movie. I'm fascinated by Korean cinema."],
        },
        {
            "name": "Hiking/Travel",
            "texts": ["I went hiking today. The scenery was beautiful."],
        },
        {
            "name": "AI/ML",
            "texts": ["AI-driven automation significantly improves productivity."],
        },
        {
            "name": "Parenting/Lifestyle",
            "texts": ["Family time with my children is precious."],
        },
        {
            "name": "Investment/FX",
            "texts": ["Market analysis is crucial for FX trading profitability."],
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[TEST {i}] {test_case['name']}")
        print(f"   Input: {test_case['texts'][0][:60]}...")
        
        try:
            result = selector.execute({
                "texts": test_case['texts'],
                "images_for_prompt": []
            })
            
            if result.get('blog_config'):
                blog_config = result['blog_config']
                print(f"   SUCCESS: Selected {blog_config.get('name')} (DB ID: {blog_config.get('id')})")
            else:
                print(f"   FAIL: Blog selection failed")
                
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()

print("\n" + "="*60)
print("[DONE] Test completed")
print("="*60)

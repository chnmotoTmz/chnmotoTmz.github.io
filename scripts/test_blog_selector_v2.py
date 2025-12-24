#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.blog_config import BlogConfig
from src.tasks.blog_selector_v2_task import BlogSelectorTaskV2

blogs = BlogConfig.get_all_blogs() or {}
print('Configured blogs count:', len(blogs))
if blogs:
    first = next(iter(blogs.keys()))
    print('Using sample blog id:', first)
    task = BlogSelectorTaskV2()
    res = task.execute({'command_context': {'target_blog': first}})
    if res and res.get('blog_config'):
        print('Task result blog_config keys:', list(res.get('blog_config').keys()))
    else:
        print('Task returned no blog_config')
else:
    print('No blogs configured; skipping full execute')

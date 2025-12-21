import json
import os
import datetime
from pathlib import Path
from typing import Dict, Any

from src.framework.base_task import BaseTaskModule

class ArticleCacheTask(BaseTaskModule):
    """
    Caches the generated article data for potential reposting.
    Saves structured data instead of processed HTML content.
    """

    # 最新の記事を保存するパス（リポスト用）
    LATEST_CACHE_PATH = "data/cached_article.json"

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves the article data to cache for reposting.
        """
        title = inputs.get("title", "")
        content = inputs.get("content", "")
        
        # リポスト時の「完全コピー」防止のため、コンセプト/構成のキャッシュは保存しない
        article_concept = {}
        article_structure = []

        repost_mode = inputs.get("repost_mode")
        repost_data = inputs.get("repost_data")
        affiliate_strategy = inputs.get("affiliate_strategy", {})
        
        blog = inputs.get("blog") or {}
        post_id = inputs.get("draft_post_id") or blog.get("hatena_blog_id", "default")
        
        cache_data = {
            "post_id": post_id,
            "blog_id": blog.get("id", ""),
            "is_repost": inputs.get("is_repost", False),
            "repost_count": 0,
            "repost_history": [],
            "title": title,
            "content": content,
            "article_concept": article_concept,
            "article_structure": article_structure,
            "affiliate_strategy": affiliate_strategy,
            "thumbnail_concept": inputs.get("thumbnail_concept", ""),
            "original_content": content,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        # 個別のキャッシュファイルを保存
        cache_dir = Path("data/cached_articles")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{post_id}.json"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to cache article: {e}")
        
        # 最新の記事として cached_article.json に保存
        if not repost_mode and not repost_data:
            try:
                Path("data").mkdir(parents=True, exist_ok=True)
                with open(self.LATEST_CACHE_PATH, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Failed to cache latest article: {e}")
        
        return {"cached_data_path": str(cache_path)}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        """Returns metadata about the module."""
        return {
            "name": "ArticleCacheTask",
            "description": "Caches generated article data in structured format for reposting."
        }
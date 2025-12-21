"""
Simple article publisher service colocated with other service modules.

Relocated from ``src.services.article.simple_article_publisher``.
"""

import logging
from typing import Optional, Dict, Any

from src.database import Blog, BlogPost
from src.services.hatena_service import HatenaService
from src.services.line_service import LineService

logger = logging.getLogger(__name__)


class SimpleArticlePublisher:
    """Publishes ``BlogPost`` entities to Hatena Blog."""

    def __init__(self, line_service: Optional[LineService] = None):
        self.line = line_service or LineService()

    def publish(self, blog: Blog, post: BlogPost) -> Optional[Dict[str, Any]]:
        logger.info(f"ブログ '{blog.name}' への記事 (ID: {post.id}) の公開を試みます。")

        try:
            # バリデーション: Hatena設定が完全であることを確認
            if not blog.hatena_id:
                logger.error(f"ブログ '{blog.name}' (ID: {blog.id}) のhatena_idが設定されていません")
                return None
            if not blog.hatena_blog_id:
                logger.error(f"ブログ '{blog.name}' (ID: {blog.id}) のhatena_blog_idが設定されていません")
                return None
            if not blog.api_key:
                logger.error(f"ブログ '{blog.name}' (ID: {blog.id}) のapi_keyが設定されていません")
                return None
            
            # HatenaService expects keys: 'hatena_id', 'hatena_blog_id', 'hatena_api_key'
            blog_config = {
                "hatena_id": blog.hatena_id,
                "hatena_blog_id": blog.hatena_blog_id,
                "hatena_api_key": blog.api_key,
            }
            hatena_service = HatenaService(blog_config)

            entry = hatena_service.publish_article(
                title=post.title,
                content=post.content,
                draft=False,
                content_type='text/x-markdown'
            )

            if entry and entry.get('url'):
                logger.info(f"はてなブログへの公開に成功しました。 URL: {entry['url']}")
                return entry

            logger.error(f"記事 (ID: {post.id}) のはてなブログへの公開に失敗しました。レスポンス: {entry}")
            return None

        except Exception as e:
            logger.error(f"記事 (ID: {post.id}) の公開中に例外が発生しました: {e}", exc_info=True)
            return None


__all__ = ["SimpleArticlePublisher"]

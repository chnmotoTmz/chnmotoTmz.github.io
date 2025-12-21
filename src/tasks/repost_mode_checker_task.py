"""
RepostModeCheckerTask - リポストモードを判定し、構造化データIDを取得するタスク
"""
import logging
import os
import json
from typing import Dict, Any, Optional
from sqlalchemy.exc import SQLAlchemyError

from src.database import db, StructuredPost
from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)

class RepostModeCheckerTask(BaseTaskModule):
    """
    リポストモードを判定し、構造化データIDを取得するタスク
    """
    
    CACHE_FILE = "data/cached_article.json"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    @staticmethod
    def get_module_info():
        return {
            "name": "RepostModeCheckerTask"
        }

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        command_context = inputs.get("command_context", {})
        style_prompt = inputs.get("style_prompt")
        
        logger.info("Checking repost mode from command_context")
        
        repost_target = command_context.get('repost_target')
        is_repost_flag = command_context.get('is_repost', False)
        
        if not repost_target and not is_repost_flag:
            return {
                "is_repost": False,
                "structured_post_id": None,
                "repost_mode": None,
                "repost_data": None,
                "cleaned_texts": inputs.get("cleaned_texts", [])
            }
        
        if repost_target == "cached" or (is_repost_flag and not repost_target):
            cached_data = self._load_cached_article()
            if cached_data:
                repost_mode = "styled" if style_prompt else "pure"
                cleaned_texts = inputs.get("cleaned_texts", []) or []
                if not cleaned_texts:
                    title = cached_data.get('title', '無題')
                    content = cached_data.get('content', '')
                    text_content = f"【リポスト元記事】\nタイトル: {title}\n\n本文:\n{content}"
                    cleaned_texts = [text_content]

                if "article_concept" in cached_data:
                    del cached_data["article_concept"]
                if "article_structure" in cached_data:
                    del cached_data["article_structure"]
                
                return {
                    "is_repost": False,
                    "structured_post_id": None,
                    "repost_mode": repost_mode,
                    "repost_data": cached_data,
                    "cleaned_texts": cleaned_texts
                }
            else:
                return {
                    "is_repost": False,
                    "structured_post_id": None,
                    "repost_mode": None,
                    "repost_data": None,
                    "cleaned_texts": inputs.get("cleaned_texts", [])
                }
        
        structured_post_id = self._resolve_repost_target(repost_target)
        if not structured_post_id:
            raise ValueError(f"Repost target not found: {repost_target}")
        
        repost_mode = "styled" if style_prompt else "pure"
        
        return {
            "is_repost": True,
            "structured_post_id": structured_post_id,
            "repost_mode": repost_mode,
            "repost_data": None,
            "cleaned_texts": inputs.get("cleaned_texts", [])
        }

    def _load_cached_article(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.CACHE_FILE):
            return None
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load cached article: {e}")
            return None

    def _resolve_repost_target(self, target: str) -> Optional[int]:
        if target.startswith('@'):
            target = target[1:]
        try:
            structured_post = StructuredPost.query.filter_by(reference_id=target).first()
            if structured_post:
                return structured_post.id
            try:
                post_id = int(target)
                structured_post = StructuredPost.query.get(post_id)
                if structured_post:
                    return post_id
            except ValueError:
                pass
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error resolving repost target: {e}")
            raise
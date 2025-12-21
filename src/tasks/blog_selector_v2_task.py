from typing import Dict, Any, List, Optional, Tuple
import logging
import re
import json
import os
import threading

from src.framework.base_task import BaseTaskModule
from src.services.unified_llm_facade import UnifiedLLMFacade
from src.blog_config import BlogConfig
from src.database import db, Blog

logger = logging.getLogger(__name__)

class BlogSelectorTaskV2(BaseTaskModule):
    """
    V2 Blog Selector.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.llm_service = UnifiedLLMFacade()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cmd_ctx = inputs.get("command_context", {})
        cleaned_texts = inputs.get("cleaned_texts", [])
        style_prompt = inputs.get("style_prompt")
        images = inputs.get("images_for_prompt", [])

        try:
            all_blogs = BlogConfig.get_all_blogs()
            if not all_blogs: return self._error_response()

            valid_blogs = {bid: cfg for bid, cfg in all_blogs.items() if cfg.get('hatena_blog_id')}
            if not valid_blogs: return self._error_response()

            selected_blog_id: Optional[str] = None
            repost_data = None
            action = cmd_ctx.get("action", "GENERATE")
            target_keyword = cmd_ctx.get("target_blog")
            is_repost = cmd_ctx.get("is_repost", False)

            if action == "REPOST" or is_repost:
                repost_data = self._load_cached_article()
                if repost_data:
                    if style_prompt:
                        cleaned_texts = [f"Original Title:\n{repost_data.get('title')}\n\nOriginal Content:\n{repost_data.get('content')}"]
                    else:
                        cleaned_texts = []

            if target_keyword:
                selected_blog_id = self._select_blog_by_keyword(target_keyword, valid_blogs)

            if not selected_blog_id:
                if len(valid_blogs) == 1:
                    selected_blog_id = next(iter(valid_blogs.keys()))
                else:
                    selected_blog_id = self._select_blog(cleaned_texts, images, valid_blogs)

            if not selected_blog_id:
                selected_blog_id = next(iter(valid_blogs.keys()))

            selected_yaml_config = BlogConfig.get_blog_config(selected_blog_id)
            blog_db_entry = self._get_or_create_blog_entry(selected_yaml_config)
            if not blog_db_entry: return self._error_response()

            blog_config_dict = {c.name: getattr(blog_db_entry, c.name) for c in blog_db_entry.__table__.columns}
            
            return {
                "blog_config": blog_config_dict,
                "cleaned_texts": cleaned_texts,
                "style_prompt": style_prompt,
                "repost_data": repost_data
            }

        except Exception as e:
            logger.error(f"Failed to select blog: {e}")
            return self._error_response()

    def _error_response(self) -> Dict[str, Any]:
        return {"blog_config": None, "cleaned_texts": [], "style_prompt": None, "repost_data": None}

    def _load_cached_article(self) -> Optional[Dict[str, Any]]:
        try:
            cache_path = os.path.join("data", "cached_article.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except: pass
        return None

    def _select_blog_by_keyword(self, keyword: str, blogs: Dict[str, Any]) -> str:
        prompt = f"Select blog ID for keyword '{keyword}':\n" + "\n".join([f"ID: {bid}, Name: {cfg.get('blog_name')}" for bid, cfg in blogs.items()])
        prompt += "\nOutput JSON: {'blog_id': '...'}"
        try:
            res = self.llm_service.generate_text(prompt=prompt, temperature=0.1)
            parsed = self._extract_json(res)
            if parsed and parsed.get('blog_id'): return parsed['blog_id']
        except: pass
        return list(blogs.keys())[0]

    def _select_blog(self, texts: List[str], images: List[Dict], blogs: Dict[str, Any]) -> str:
        content = "\n".join(texts[:3])
        prompt = f"Select blog ID for content:\n{content[:500]}\n" + "\n".join([f"ID: {bid}, Name: {cfg.get('blog_name')}" for bid, cfg in blogs.items()])
        prompt += "\nOutput JSON: {'blog_id': '...'}"
        try:
            res = self.llm_service.generate_text(prompt=prompt, temperature=0.2)
            parsed = self._extract_json(res)
            if parsed and parsed.get('blog_id'): return parsed['blog_id']
        except: pass
        return list(blogs.keys())[0]

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            match = re.search(r"\{{.*?\}}", text, re.DOTALL)
            if match: return json.loads(match.group(0).replace("'", '"'))
        except: pass
        return None

    def _get_or_create_blog_entry(self, yaml_config: Dict[str, Any]) -> Optional[Blog]:
        hatena_blog_id = yaml_config.get('hatena_blog_id')
        if not hatena_blog_id: return None
        blog = Blog.query.filter_by(hatena_blog_id=hatena_blog_id).first()
        if not blog:
            blog = Blog(name=yaml_config.get('blog_name', 'Unknown'), hatena_id=yaml_config.get('hatena_id', ''), hatena_blog_id=hatena_blog_id, api_key=yaml_config.get('hatena_api_key', ''))
            db.session.add(blog)
        else:
            blog.api_key = yaml_config.get('hatena_api_key') or blog.api_key
        db.session.commit()
        return blog

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "BlogSelectorTaskV2"}

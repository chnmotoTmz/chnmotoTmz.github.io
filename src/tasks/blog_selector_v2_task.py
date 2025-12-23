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
from src.processes.blog_selection import BlogSelectorProcess

logger = logging.getLogger(__name__)

class BlogSelectorTaskV2(BaseTaskModule):
    """
    V2 Blog Selector.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.llm_service = UnifiedLLMFacade()
        self.process = BlogSelectorProcess()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cmd_ctx = inputs.get("command_context", {})
        cleaned_texts = inputs.get("cleaned_texts", [])
        style_prompt = inputs.get("style_prompt")
        images = inputs.get("images_for_prompt", [])

        try:
            all_blogs = BlogConfig.get_all_blogs()
            if not all_blogs: return self._error_response()

            # Filter blogs based on content and validation (respect exclude_keywords)
            content_sample = "\n".join(cleaned_texts[:5])
            valid_blogs = self.process.filter_blogs(all_blogs, content_sample)
            
            if not valid_blogs:
                logger.warning("No blogs matched filtering. Falling back to all valid blogs.")
                valid_blogs = self.process.filter_blogs(all_blogs, "")
            
            if not valid_blogs: return self._error_response()

            selected_blog_id: Optional[str] = None
            repost_data = None
            action = cmd_ctx.get("action", "GENERATE")
            target_keyword = cmd_ctx.get("target_blog")
            is_repost = cmd_ctx.get("is_repost", False)

            logger.info(f"--- Blog Selection Trace (V2) ---")
            logger.info(f"Available Candidates: {list(valid_blogs.keys())}")
            logger.info(f"Command Target: '{target_keyword}'")

            if action == "REPOST" or is_repost:
                repost_data = self._load_cached_article()
                if repost_data:
                    if style_prompt:
                        cleaned_texts = [f"Original Title:\n{repost_data.get('title')}\n\nOriginal Content:\n{repost_data.get('content')}"]
                    else:
                        cleaned_texts = []

            # Priority 1: Explicit Command Keyword (e.g. !主婦)
            if target_keyword:
                logger.info(f"Priority Selection: Using keyword '{target_keyword}'")
                selected_blog_id = self._select_blog_by_keyword(target_keyword, valid_blogs)
                if selected_blog_id:
                    logger.info(f"✅ [Case A] Selected by Command Keyword: {selected_blog_id}")

            # Priority 2: Single Blog Case
            if not selected_blog_id and len(valid_blogs) == 1:
                selected_blog_id = next(iter(valid_blogs.keys()))
                logger.info(f"✅ [Case B] Auto-selected Single Candidate: {selected_blog_id}")

            # Priority 3: Content-based LLM Selection
            if not selected_blog_id:
                logger.info("ℹ️ [Case C] Fallback to Content Analysis (LLM)")
                selected_blog_id = self._select_blog(cleaned_texts, images, valid_blogs)
                if selected_blog_id:
                    logger.info(f"✅ [Case C] Selected by Content Analysis: {selected_blog_id}")

            # Final Fallback
            if not selected_blog_id:
                selected_blog_id = next(iter(valid_blogs.keys()))
                logger.warning(f"⚠️ [Final Fallback] Selecting first available: {selected_blog_id}")

            logger.info(f"🏁 Final Selection: {selected_blog_id}")
            logger.info(f"---------------------------------")

            selected_yaml_config = BlogConfig.get_blog_config(selected_blog_id)
            if not selected_yaml_config:
                raise ValueError(f"Selected blog ID '{selected_blog_id}' not found in configuration.")

            blog_db_entry = self._get_or_create_blog_entry(selected_yaml_config)
            if not blog_db_entry:
                raise ValueError(f"Could not initialize database entry for blog '{selected_blog_id}'.")

            blog_config_dict = {c.name: getattr(blog_db_entry, c.name) for c in blog_db_entry.__table__.columns}
            # Add back metadata from YAML
            blog_config_dict['blog_name'] = selected_yaml_config.get('blog_name', blog_db_entry.name)
            blog_config_dict['description'] = selected_yaml_config.get('description', '')
            blog_config_dict['prompt_file'] = selected_yaml_config.get('prompt_file', '')
            
            logger.info(f"🏁 Final Selection: {selected_blog_id} ({blog_config_dict['blog_name']})")
            logger.info(f"---------------------------------")

            return {
                "blog_config": blog_config_dict,
                "cleaned_texts": cleaned_texts,
                "style_prompt": style_prompt,
                "repost_data": repost_data
            }

        except Exception as e:
            logger.error(f"Failed to select blog: {e}", exc_info=True)
            raise  # Trigger handle_error

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

    def _select_blog_by_keyword(self, keyword: str, blogs: Dict[str, Any]) -> Optional[str]:
        keyword_lower = keyword.lower()
        
        # 1. Direct ID match
        if keyword_lower in blogs:
            logger.info(f"Direct ID match found: {keyword_lower}")
            return keyword_lower
            
        # 2. Direct Name match
        for bid, cfg in blogs.items():
            if keyword_lower == cfg.get('blog_name', '').lower():
                logger.info(f"Direct Name match found: {bid}")
                return bid
                
        # 3. Partial Name match
        for bid, cfg in blogs.items():
            if keyword_lower in cfg.get('blog_name', '').lower():
                logger.info(f"Partial Name match found: {bid}")
                return bid

        # 4. Predefined Keywords match
        for bid, cfg in blogs.items():
            keywords = [k.lower() for k in cfg.get('keywords', [])]
            if keyword_lower in keywords:
                logger.info(f"Keyword list match found: {bid}")
                return bid

        # 5. LLM Fallback for semantic matching
        logger.info(f"No direct match for '{keyword}'. Falling back to LLM semantic matching.")
        prompt = f"Select one blog ID that best matches the user keyword '{keyword}'.\nAvailable Blogs:\n" 
        prompt += "\n".join([f"- ID: {bid}, Name: {cfg.get('blog_name')}, Description: {cfg.get('description')}" for bid, cfg in blogs.items()])
        prompt += "\n\nReturn ONLY a JSON object: {\"blog_id\": \"...\"}"
        try:
            res = self.llm_service.generate_text(prompt=prompt, temperature=0.1)
            parsed = self._extract_json(res)
            blog_id = parsed.get('blog_id') if parsed else None
            if blog_id in blogs: 
                return blog_id
        except Exception as e:
            logger.warning(f"Keyword selection LLM failed: {e}")
        return None

    def _select_blog(self, texts: List[str], images: List[Dict], blogs: Dict[str, Any]) -> Optional[str]:
        content = "\n".join(texts[:3])
        prompt = f"Analyze the content and select the most appropriate blog ID.\nContent:\n{content[:500]}\n\nAvailable Blogs:\n"
        prompt += "\n".join([f"- ID: {bid}, Name: {cfg.get('blog_name')}" for bid, cfg in blogs.items()])
        prompt += "\n\nReturn ONLY a JSON object: {\"blog_id\": \"...\"}"
        try:
            res = self.llm_service.generate_text(prompt=prompt, temperature=0.2)
            parsed = self._extract_json(res)
            if parsed and parsed.get('blog_id') in blogs: 
                return parsed['blog_id']
        except Exception as e:
            logger.warning(f"Content-based selection LLM failed: {e}")
        return None

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            # Look for JSON block or outermost braces
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
            cleaned = match.group(1) if match else text
            
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1:
                json_str = cleaned[start:end+1]
                return json.loads(json_str.replace("'", '"'))
        except Exception as e:
            logger.debug(f"JSON extraction failed: {e}")
        return None

    def _get_or_create_blog_entry(self, yaml_config: Dict[str, Any]) -> Optional[Blog]:
        if not yaml_config: return None
        hatena_blog_id = yaml_config.get('hatena_blog_id')
        if not hatena_blog_id: return None
        
        try:
            blog = Blog.query.filter_by(hatena_blog_id=hatena_blog_id).first()
            if not blog:
                logger.info(f"Creating new DB entry for blog: {hatena_blog_id}")
                blog = Blog(
                    name=yaml_config.get('blog_name', 'Unknown'), 
                    hatena_id=yaml_config.get('hatena_id', ''), 
                    hatena_blog_id=hatena_blog_id, 
                    api_key=yaml_config.get('hatena_api_key', '')
                )
                db.session.add(blog)
            else:
                # Update API key if it changed in YAML
                if yaml_config.get('hatena_api_key'):
                    blog.api_key = yaml_config.get('hatena_api_key')
            
            db.session.commit()
            return blog
        except Exception as e:
            logger.error(f"Database error during blog selection: {e}")
            db.session.rollback()
            return None

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "BlogSelectorTaskV2"}

from typing import Dict, Any, List, Optional, Tuple
import logging
import json
import threading

from src.framework.base_task import BaseTaskModule
from src.processes.blog_selection import BlogSelectorProcess
from src.services.unified_llm_facade import UnifiedLLMFacade
from src.blog_config import BlogConfig
from src.database import db, Blog

logger = logging.getLogger(__name__)

class BlogSelectorTask(BaseTaskModule):
    """
    Selects the most appropriate blog based on message content using LLM analysis.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = UnifiedLLMFacade()
        self.process = BlogSelectorProcess()
        logger.info("BlogSelectorTask initialized")

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        texts = inputs.get("texts", [])
        command_context = inputs.get("command_context")
        cleaned_texts_input = inputs.get("cleaned_texts")
        style_prompt_input = inputs.get("style_prompt")
        images = inputs.get("images_for_prompt", [])

        is_repost_mode = False
        repost_prompt = ""

        if command_context and cleaned_texts_input is not None:
             texts = cleaned_texts_input
             command_keyword = command_context.get("target_blog")
             ctx_type = command_context.get("type")
             is_repost_mode = ctx_type in ["REPOST", "REPOST_REWRITE"]
             repost_keyword = command_context.get("target_blog") if is_repost_mode else None
             repost_prompt = style_prompt_input or ""
        else:
             if texts and isinstance(texts[0], dict) and "summary" in texts[0]:
                texts = [ws.get("summary", "") for ws in texts]
             cleaned_texts, command_keyword, repost_keyword, style_prompts = self.process.parse_commands(texts)
             repost_prompt = " / ".join(style_prompts) if style_prompts else ""
             texts = cleaned_texts

        all_blogs = BlogConfig.get_all_blogs()
        if not all_blogs:
            logger.error("No blogs available in configuration")
            return {"blog_config": None}

        selected_blog_id = None
        content_text = "\n".join(texts[:5])
        valid_blogs = self.process.filter_blogs(all_blogs, content_text)

        if not valid_blogs:
            valid_blogs = self.process.filter_blogs(all_blogs, "")
            if not valid_blogs: return {"blog_config": None}

        logger.info(f"--- Blog Selection Trace ---")
        logger.info(f"Available Candidates: {list(valid_blogs.keys())}")
        logger.info(f"Command Keyword: '{command_keyword}'")
        logger.info(f"Repost Mode: {is_repost_mode} (Keyword: '{repost_keyword}')")

        # Case A: Explicit Command (Prioritize immediately)
        if command_keyword:
            logger.info(f"Prioritizing explicit command keyword: {command_keyword}")
            prompt = self.process.create_keyword_selection_prompt(command_keyword, valid_blogs)
            try:
                # Use a slightly higher temperature to allow for variations in how the model interprets the keyword match
                # but keep it focused.
                response = self.llm_service.generate_text(prompt=prompt, temperature=0.1, max_tokens=200)
                sel_id, _ = self.process.parse_selection_response(response, list(valid_blogs.keys()))
                resolved_id = self.process.resolve_blog_id(sel_id, valid_blogs)
                if resolved_id:
                    selected_blog_id = resolved_id
                    logger.info(f"✅ [Case A] Selected by Command: {selected_blog_id}")
                else:
                    logger.warning(f"❌ [Case A] Command selection failed. LLM response: {response[:100]}...")
            except Exception as e:
                logger.warning(f"❌ [Case A] Keyword selection exception: {e}")

        # Case B: Repost Keyword
        if is_repost_mode and repost_keyword and not selected_blog_id:
             prompt = self.process.create_keyword_selection_prompt(repost_keyword, valid_blogs)
             try:
                response = self.llm_service.generate_text(prompt=prompt, temperature=0.1, max_tokens=200)
                sel_id, _ = self.process.parse_selection_response(response, list(valid_blogs.keys()))
                selected_blog_id = self.process.resolve_blog_id(sel_id, valid_blogs)
                if selected_blog_id:
                    logger.info(f"✅ [Case B] Selected by Repost Keyword: {selected_blog_id}")
             except Exception:
                pass

        # Case C: Single Blog
        if len(valid_blogs) == 1 and not selected_blog_id:
            selected_blog_id = next(iter(valid_blogs.keys()))
            logger.info(f"✅ [Case C] Auto-selected Single Candidate: {selected_blog_id}")

        # Case D: LLM Selection (Content Analysis)
        if not selected_blog_id:
            logger.info("ℹ️ [Case D] Fallback to Content Analysis (LLM)")
            selection_content = "\n".join(texts[:5])
            image_descs = [img.get('description', '') for img in images[:3]]
            prompt = self.process.create_selection_prompt(selection_content, image_descs, valid_blogs)
            try:
                response = self.llm_service.generate_text(prompt=prompt, temperature=0.2, max_tokens=500)
                sel_id, _ = self.process.parse_selection_response(response, list(valid_blogs.keys()))
                selected_blog_id = self.process.resolve_blog_id(sel_id, valid_blogs)
                if selected_blog_id:
                    logger.info(f"✅ [Case D] Selected by Content Analysis: {selected_blog_id}")
                else:
                    heuristic_id = self.process.heuristic_select(selection_content, valid_blogs)
                    selected_blog_id = heuristic_id
                    logger.info(f"✅ [Case D] Fallback to Heuristic: {selected_blog_id}")
            except Exception as e:
                logger.warning(f"❌ [Case D] Content analysis failed: {e}")
                selected_blog_id = self.process.heuristic_select(selection_content, valid_blogs)
                logger.info(f"✅ [Case D] Emergency Heuristic: {selected_blog_id}")

        if not selected_blog_id:
             selected_blog_id = next(iter(valid_blogs.keys()))
             logger.warning(f"⚠️ [Final Fallback] Selecting first available: {selected_blog_id}")

        logger.info(f"🏁 Final Selection: {selected_blog_id}")
        logger.info(f"------------------------------")

        selected_yaml_config = BlogConfig.get_blog_config(selected_blog_id)
        blog_db_entry = self._get_or_create_blog_entry(selected_yaml_config)
        if not blog_db_entry: return {"blog_config": None}

        blog_config_dict = {c.name: getattr(blog_db_entry, c.name) for c in blog_db_entry.__table__.columns}
        
        repost_data = None
        if is_repost_mode:
            repost_data, extra_text = self._load_last_article_for_repost(repost_prompt)
            if extra_text: texts = [extra_text]
            elif repost_data: texts = []

        return {
            "blog_config": blog_config_dict,
            "cleaned_texts": texts,
            "repost_data": repost_data,
            "style_prompt": repost_prompt
        }

    def _get_or_create_blog_entry(self, yaml_config: Dict[str, Any]) -> Optional[Blog]:
        hatena_blog_id = yaml_config.get('hatena_blog_id')
        if not hatena_blog_id: return None
        try:
            blog = Blog.query.filter_by(hatena_blog_id=hatena_blog_id).first()
            if blog:
                blog.name = yaml_config.get('blog_name') or blog.name
                blog.hatena_id = yaml_config.get('hatena_id') or blog.hatena_id
                blog.api_key = yaml_config.get('hatena_api_key') or blog.api_key
                db.session.commit()
                return blog
            else:
                new_blog = Blog(name=yaml_config.get('blog_name', 'Unknown'), hatena_id=yaml_config.get('hatena_id', ''), hatena_blog_id=hatena_blog_id, api_key=yaml_config.get('hatena_api_key', ''))
                db.session.add(new_blog)
                db.session.commit()
                return new_blog
        except Exception:
            db.session.rollback()
            return None

    def _load_last_article_for_repost(self, repost_prompt: str) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            path = os.path.join("data", "last_article.json")
            if not os.path.exists(path): return None, None
            with open(path, "r", encoding="utf-8") as f:
                last_article = json.load(f)
            if not last_article: return None, None
            if repost_prompt:
                context = f"【元記事タイトル】\n{last_article.get('title')}\n\n【元記事本文】\n{last_article.get('content')}"
                return None, f"{repost_prompt}\n\n{context}"
            else:
                return last_article, None
        except Exception:
            return None, None

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "BlogSelectorTask", "description": "Selects blog based on content analysis."}
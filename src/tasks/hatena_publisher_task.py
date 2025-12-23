from typing import Dict, Any
import json
import os
import re
import logging
from src.framework.base_task import BaseTaskModule
from src.services.hatena_service import HatenaService
from src.database import db, BlogPost, Blog

logger = logging.getLogger(__name__)

class HatenaPublisherTask(BaseTaskModule):
    """
    Publishes an article to Hatena Blog.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        blog_data: Dict = inputs.get("blog")
        post_id: int = inputs.get("post_id")
        tags: list = inputs.get("tags", [])
        article_concept: Dict = inputs.get("article_concept", {})

        if not tags and article_concept:
            if article_concept.get('genre'):
                tags.append(article_concept['genre'])
            if article_concept.get('keywords'):
                tags.extend(article_concept['keywords'])
            tags = list(dict.fromkeys(tags))[:5]

        if not blog_data or post_id is None:
            logger.warning("Missing post_id or blog input. Skipping publish.")
            return {"hatena_entry": None}

        try:
            post = db.session.query(BlogPost).get(post_id)
            if not post: raise ValueError(f"Post {post_id} not found.")

            blog = db.session.query(Blog).get(blog_data['id'])
            if not blog: raise ValueError(f"Blog {blog_data['id']} not found.")

            blog_credentials = {
                'hatena_id': blog.hatena_id,
                'hatena_blog_id': blog.hatena_blog_id,
                'hatena_api_key': blog.api_key
            }
            hatena_service = HatenaService(blog_config=blog_credentials)

            # --- Physical Content Fixes ---
            final_content = post.content
            
            # 1. Force Hatena TOC at the very top (after thumbnail)
            if "[:contents]" not in final_content:
                # If there's a thumbnail, insert after it
                # Robust match for thumbnail
                thumb_match = re.match(r"^\s*(?:(!\[.*?\]\(http.*?\))|(?:\[(!\[.*?\]\(http.*?\))\]\(http.*?\)))\s*\n*", final_content)
                if thumb_match:
                    thumb_part = thumb_match.group(0).strip()
                    rest_part = final_content[len(thumb_match.group(0)):].lstrip()
                    final_content = f"{thumb_part}\n\n[:contents]\n\n{rest_part}"
                else:
                    final_content = f"[:contents]\n\n{final_content.lstrip()}"
            else:
                # Even if it exists, ensure it has clear space
                final_content = final_content.replace("[:contents]", "\n\n[:contents]\n\n")
                # Clean up any triple newlines created
                final_content = re.sub(r'\n{3,}', '\n\n', final_content)
            
            logger.info("Publishing to Hatena with forced TOC.")

            entry = hatena_service.publish_article(
                title=post.title,
                content=final_content,
                tags=tags,
                draft=False
            )

            if not entry or not entry.get('url'):
                raise RuntimeError("Publishing failed.")

            # Save last published info
            try:
                os.makedirs("data", exist_ok=True)
                with open("data/last_published.json", "w", encoding="utf-8") as f:
                    json.dump(entry, f, ensure_ascii=False, indent=2)
            except: pass

            return {"hatena_entry": entry}

        except Exception as e:
            logger.error(f"Failed to publish: {e}")
            raise

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "HatenaPublisher",
            "description": "Publishes article to Hatena Blog."
        }
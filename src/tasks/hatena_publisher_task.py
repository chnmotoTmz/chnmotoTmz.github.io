from typing import Dict, Any
import json
import os
import re
import logging
from src.framework.base_task import BaseTaskModule
from src.services.hatena_service import HatenaService
from src.database import db, BlogPost, Blog
from src.services.imgur_service import ImgurService
from src.config import Config

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

            # Resolve blog DB entry: prioritize 'hatena_blog_id' over 'id'
            if 'hatena_blog_id' in blog_data:
                hatena_blog_id = blog_data['hatena_blog_id']
                blog = db.session.query(Blog).filter_by(hatena_blog_id=hatena_blog_id).first()
            elif 'id' in blog_data:
                # Try as database ID first, then as hatena_blog_id
                blog_id = blog_data['id']
                blog = db.session.query(Blog).get(blog_id)
                if not blog:
                    # Maybe 'id' is actually the hatena_blog_id string
                    blog = db.session.query(Blog).filter_by(hatena_blog_id=str(blog_id)).first()
            else:
                raise ValueError("Blog data missing 'id' or 'hatena_blog_id'")

            if not blog: raise ValueError(f"Blog not found in database.")

            blog_credentials = {
                'hatena_id': blog.hatena_id,
                'hatena_blog_id': blog.hatena_blog_id,
                'hatena_api_key': blog.api_key
            }
            hatena_service = HatenaService(blog_config=blog_credentials)

            # --- Physical Content Fixes ---
            final_content = post.content

            # 0. Inject Thumbnail if provided in inputs but missing in content
            thumbnail_input = inputs.get("thumbnail") or inputs.get("thumbnail_path") or inputs.get("thumbnail_url")
            if thumbnail_input:
                # Basic check to avoid duplication (checking filename or url)
                # If the content doesn't seem to start with an image or contain this specific thumbnail
                if thumbnail_input not in final_content:
                    logger.info(f"Injecting thumbnail from inputs: {thumbnail_input}")
                    
                    # Upload if local
                    uploaded_thumb_url = thumbnail_input
                    if os.path.exists(thumbnail_input) or thumbnail_input.startswith("file://"):
                        try:
                            imgur = ImgurService()
                            p = thumbnail_input
                            if p.startswith('file://'):
                                p = p[len('file://'):]
                            if not os.path.isabs(p):
                                p = os.path.join(os.getcwd(), p)
                            
                            if os.path.exists(p):
                                resp = imgur.upload_image(p)
                                if resp and resp.get('success') and resp.get('link'):
                                    uploaded_thumb_url = resp.get('link')
                                    logger.info(f"Uploaded thumbnail to: {uploaded_thumb_url}")
                                else:
                                    logger.warning(f"Failed to upload thumbnail {p}: {resp}")
                        except Exception as e:
                            logger.error(f"Error uploading thumbnail {thumbnail_input}: {e}")

                    # Prepend to content
                    final_content = f"![Thumbnail]({uploaded_thumb_url})\n\n" + final_content

            # Replace local image srcs (file://, local paths) by uploading to Imgur when possible
            try:
                imgur = ImgurService()
                def _upload_local(src_path: str) -> str:
                    # Normalize file:// prefix
                    p = src_path
                    if p.startswith('file://'):
                        p = p[len('file://'):]
                    # If it is not absolute, try relative to CWD
                    if not os.path.isabs(p):
                        p = os.path.join(os.getcwd(), p)
                    if not os.path.exists(p):
                        logger.warning(f"Local image path not found for upload: {p}")
                        return src_path
                    try:
                        resp = imgur.upload_image(p)
                        if resp and resp.get('success') and resp.get('link'):
                            return resp.get('link')
                        logger.warning(f"Imgur upload failed for {p}: {resp}")
                    except Exception as e:
                        logger.warning(f"Imgur upload exception for {p}: {e}")
                    return src_path

                # Find all <img src='...'> or src="..."
                def _replace_src(match):
                    src = match.group(1)
                    if src.startswith('file://') or src.startswith('/') or src.startswith('./') or src.startswith(Config.UPLOAD_FOLDER):
                        new = _upload_local(src)
                        return f"src=\"{new}\""
                    return match.group(0)

                final_content = re.sub(r'src=["\']([^"\']+)["\']', _replace_src, final_content)
            except Exception as e:
                logger.warning(f"Image uploading before publish failed: {e}")

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
            
            # Update DB with final content (including thumbnail and TOC)
            try:
                post.content = final_content
                db.session.commit()
            except Exception as e:
                logger.warning(f"Failed to update post content in DB: {e}")

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
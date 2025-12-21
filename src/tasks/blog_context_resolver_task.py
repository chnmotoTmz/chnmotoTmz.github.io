from typing import Dict, Any, Optional
import logging
from src.framework.base_task import BaseTaskModule
from src.blog_config import BlogConfig
from src.database import db, Blog

logger = logging.getLogger(__name__)

class BlogContextResolverTask(BaseTaskModule):
    """
    Guarantees that a blog context is set early in the workflow.
    Resolves blog based on command context or falls back to a default.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves the blog context.
        """
        command_context = inputs.get("command_context", {})
        default_blog_id = inputs.get("default_blog", "政治") # Default to '政治' if nothing else works, assuming it exists

        # 1. Try to get blog from command context (e.g., explicit target)
        target_blog_id = command_context.get("target_blog")

        blog_config = None

        if target_blog_id:
            blog_config = BlogConfig.get_blog_config(target_blog_id)
            if blog_config:
                logger.info(f"Resolved blog from command context: {target_blog_id}")

        # 2. If not found, try default
        if not blog_config:
            blog_config = BlogConfig.get_blog_config(default_blog_id)
            if blog_config:
                logger.info(f"Resolved blog using default: {default_blog_id}")
            else:
                # 3. If default fails, pick the first available
                all_blogs = BlogConfig.get_all_blogs()
                if all_blogs:
                    first_id = next(iter(all_blogs))
                    blog_config = all_blogs[first_id]
                    logger.info(f"Resolved blog using fallback (first available): {first_id}")
                else:
                    logger.error("No blogs defined in configuration!")
                    # We can't proceed without a blog, but we must return something to avoid NoneType errors downstream if they don't check.
                    # Ideally, we should raise an error or stop, but the goal is to guarantee context.
                    # We'll return an empty dict but log a critical error.
                    return {"blog": {}}

        # 4. Ensure DB entry exists (similar to BlogSelectorTask)
        blog_db_entry = self._get_or_create_blog_entry(blog_config)

        if not blog_db_entry:
            logger.error("Failed to get/create DB entry for blog.")
            return {"blog": {}}

        # Convert to dictionary
        blog_data = {c.name: getattr(blog_db_entry, c.name) for c in blog_db_entry.__table__.columns}

        return {
            "blog": blog_data
        }

    def _get_or_create_blog_entry(self, yaml_config: Dict[str, Any]) -> Optional[Blog]:
        """DB IO Helper."""
        hatena_blog_id = yaml_config.get('hatena_blog_id')
        if not hatena_blog_id: return None
        try:
            blog = Blog.query.filter_by(hatena_blog_id=hatena_blog_id).first()
            if blog:
                # Update existing just in case config changed
                blog.name = yaml_config.get('blog_name') or blog.name
                blog.hatena_id = yaml_config.get('hatena_id') or blog.hatena_id
                blog.api_key = yaml_config.get('hatena_api_key') or blog.api_key
                db.session.commit()
                return blog
            else:
                new_blog = Blog(
                    name=yaml_config.get('blog_name', 'Unknown'),
                    hatena_id=yaml_config.get('hatena_id', ''),
                    hatena_blog_id=hatena_blog_id,
                    api_key=yaml_config.get('hatena_api_key', '')
                )
                db.session.add(new_blog)
                db.session.commit()
                return new_blog
        except Exception as e:
            logger.error("DB Error in BlogContextResolver: %s", e)
            db.session.rollback()
            return None

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "BlogContextResolverTask",
            "description": "Resolves the blog context ensuring it is never null.",
            "inputs": {
                "command_context": "Dict",
                "default_blog": "str"
            },
            "outputs": {
                "blog": "Dict[str, Any]"
            }
        }

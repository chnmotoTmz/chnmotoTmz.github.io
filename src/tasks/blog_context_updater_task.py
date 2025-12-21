from typing import Dict, Any
import logging
from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)

class BlogContextUpdaterTask(BaseTaskModule):
    """
    Updates the blog context with a new selection if valid, otherwise keeps the existing one.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        current_blog = inputs.get("current_blog")
        new_blog = inputs.get("new_blog")

        final_blog = current_blog

        if new_blog and isinstance(new_blog, dict) and new_blog.get("id"):
            logger.info(f"Updating blog context to selected blog: {new_blog.get('name')} (ID: {new_blog.get('id')})")
            final_blog = new_blog
        elif current_blog:
             logger.info(f"Keeping existing blog context: {current_blog.get('name')} (ID: {current_blog.get('id')})")
        else:
            logger.warning("No valid blog context available even after update check!")

        return {
            "blog": final_blog
        }

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "BlogContextUpdaterTask",
            "description": "Updates blog context if a new valid selection is made.",
            "inputs": {
                "current_blog": "Dict",
                "new_blog": "Dict"
            },
            "outputs": {
                "blog": "Dict"
            }
        }

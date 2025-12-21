"""
Finalize Post Task

This task ensures that all assets are preserved and properly linked in the final blog post.
"""

import logging
from typing import Dict, Any
from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)

class FinalizePostTask(BaseTaskModule):
    """
    Ensures that all assets are preserved and properly linked in the final blog post.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        content = inputs.get("content", "")
        thumbnail = inputs.get("thumbnail", "")
        past_articles = inputs.get("past_articles", [])
        affiliates = inputs.get("affiliates", [])

        if not content:
            logger.error("No content provided for finalization.")
            return {"error": "No content provided."}

        # Finalize the content
        finalized_content = self._finalize_content(content, thumbnail, past_articles, affiliates)

        return {
            "finalized_content": finalized_content
        }

    def _finalize_content(self, content: str, thumbnail: str, past_articles: list, affiliates: list) -> str:
        # Embed the thumbnail if not already present
        if thumbnail and thumbnail not in content:
            content = f"![Thumbnail]({thumbnail})\n\n" + content

        # Embed past articles
        if past_articles:
            past_articles_section = "\n\n## Related Articles\n" + "\n".join(f"- [{a}]({a})" for a in past_articles)
            content += past_articles_section

        # Embed affiliate links
        if affiliates:
            affiliates_section = "\n\n## Affiliate Links\n" + "\n".join(f"- [{a}]({a})" for a in affiliates)
            content += affiliates_section

        return content

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "FinalizePostTask",
            "description": "Finalizes the blog post with all assets."
        }
import logging
import re
from typing import Dict, Any, List
from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)

class AddLinkedSourcesTask(BaseTaskModule):
    """
    Appends source links to the content.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Appends source links to the content.
        
        Args:
            inputs (Dict[str, Any]): Expects 'content' (str) and 'web_summaries' (List[Dict]).
                                     Optional 'section_title' (str).

        Returns:
            Dict[str, Any]: A dictionary containing 'content_with_links'.
        """
        content: str = inputs.get("content")
        web_summaries: List[Dict] = inputs.get("web_summaries", [])
        section_title: str = inputs.get("section_title", "📚 Reference Sources")

        if not content:
            raise ValueError("Content is a required input.")

        # 1. Protect existing thumbnail
        # More robust thumbnail detection (handles ![]() and [![]()]())
        thumbnail_match = re.match(r"^\s*(?:(!\[.*?]\[http.*?])|(?:\b(!\[.*?]\[http.*?])\](http.*?)))\s*\n*", content)
        thumbnail_md = thumbnail_match.group(0) if thumbnail_match else ""
        content_no_thumb = content[len(thumbnail_md):] if thumbnail_md else content

        if not web_summaries:
            return {"content_with_links": content}

        # Avoid adding redundant sources
        if section_title in content:
            return {"content_with_links": content}

        links_md = f"\n\n## {section_title}\n\n"
        for source in web_summaries:
            title = source.get("title", "Unknown Source")
            url = source.get("url")
            if url:
                links_md += f"- [{title}]({url})\n"

        return {"content_with_links": thumbnail_md + content_no_thumb + links_md}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "AddLinkedSourcesTask",
            "description": "Appends reference links to the article.",
            "inputs": { "content": "str", "web_summaries": "List[Dict]" },
            "outputs": { "content_with_links": "str" }
        }
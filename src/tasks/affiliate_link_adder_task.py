import logging
import re
from typing import Dict, Any, List
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class AffiliateLinkAdderTask(BaseTaskModule):
    """
    Adds affiliate links to product names in article content.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        content: str = inputs.get("content", "")
        affiliate_strategy: Dict = inputs.get("affiliate_strategy", {})
        article_concept: Dict = inputs.get("article_concept", {})
        
        import re
        thumbnail_match = re.match(r"^\s*(!\[.*?\]\(http.*?\)\n*)", content)
        thumbnail_md = thumbnail_match.group(1) if thumbnail_match else ""
        content_no_thumb = content[len(thumbnail_md):] if thumbnail_md else content

        from src.utils.product_linker import insert_product_links
        product_links = {}
        web_summaries = inputs.get('web_summaries', [])
        for s in web_summaries:
            if s.get('title') and s.get('url'):
                product_links[s['title']] = s['url']
        target = affiliate_strategy.get('target_product')
        url = affiliate_strategy.get('amazon_url') or affiliate_strategy.get('rakuten_url')
        if target and url:
            product_links[target] = url
        
        updated_content = insert_product_links(content_no_thumb, product_links)

        if not updated_content:
            return {"content_with_affiliates": thumbnail_md}

        rule_based_only = self.config.get("rule_based_only", False)
        if rule_based_only:
            return {"content_with_affiliates": thumbnail_md + updated_content}

        # (Simplified LLM logic for recovery)
        return {"content_with_affiliates": thumbnail_md + updated_content}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "AffiliateLinkAdderTask", "description": "Adds affiliate links."}
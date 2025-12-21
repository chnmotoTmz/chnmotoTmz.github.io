"""
Amazon Link Remover Task - Removes or replaces Amazon links with Rakuten alternatives.
"""

import logging
import re
import urllib.parse
from typing import Dict, Any

from src.framework.base_task import BaseTaskModule
from src.services import rakuten_api

logger = logging.getLogger(__name__)


class AmazonLinkRemoverTask(BaseTaskModule):
    """Removes Amazon links and replaces them with Rakuten alternatives."""
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove or replace Amazon links in the content.
        """
        title = inputs.get("title", "")
        content = inputs.get("content", "")
        
        logger.info("Starting Amazon link removal and Rakuten replacement task.")
        
        amazon_count = 0
        replaced_count = 0
        
        # Markdown形式のAmazonリンクを検出・置換
        def replace_amazon_link(match):
            nonlocal amazon_count, replaced_count
            amazon_count += 1
            
            link_text = match.group(1)
            amazon_url = match.group(2)
            
            # 戦略1: URLのクエリパラメータから検索キーワードを抽出
            keyword = None
            query_match = re.search(r'[?&]k=([^&]+)', amazon_url)
            if query_match:
                keyword = urllib.parse.unquote(query_match.group(1))
            
            # 戦略2: リンクテキストをキーワードとして使用
            if not keyword:
                keyword = link_text.strip()
            
            # 楽天で検索
            rakuten_url = self._search_and_get_rakuten_link(keyword, link_text)
            
            if rakuten_url:
                replaced_count += 1
                return f"[{link_text}]({rakuten_url})"
            else:
                return match.group(0)
        
        # Markdown形式のAmazonリンクを置換
        content = re.sub(
            r'\[([^\]]+)\]\((https?://(?:www\.)?amazon\.co\.jp[^\)]*)\)',
            replace_amazon_link,
            content,
            flags=re.IGNORECASE
        )
        
        # 裸のAmazonリンクも検出・除去
        def remove_naked_amazon(match):
            nonlocal amazon_count
            amazon_count += 1
            return ""
        
        content = re.sub(
            r'(?<!\]\()https?://(?:www\.)?amazon\.co\.jp[^\s\)]*',
            remove_naked_amazon,
            content,
            flags=re.IGNORECASE
        )
        
        logger.info(f"Finished. Found {amazon_count} Amazon links, replaced {replaced_count}.")
        
        return {
            "title": title,
            "content": content
        }
    
    def _search_and_get_rakuten_link(self, keyword: str, fallback_text: str) -> str:
        """
        楽天で検索し、アフィリエイトリンクを取得します。
        """
        for search_keyword in [keyword, fallback_text]:
            if not search_keyword or len(search_keyword.strip()) < 2:
                continue
            
            try:
                products = rakuten_api.search_products(search_keyword, max_retries=2)
                
                if isinstance(products, list) and len(products) > 0:
                    product = products[0]
                    item_url = product.get('itemUrl')
                    
                    if item_url:
                        affiliate_url = rakuten_api.generate_affiliate_link(item_url)
                        if affiliate_url:
                            return affiliate_url
            except Exception:
                continue
        
        return ""
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "AmazonLinkRemoverTask",
            "description": "Removes Amazon links and replaces them with Rakuten alternatives."
        }
import re
import json
import logging
from typing import Dict, Any, List

from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService
from src.services import rakuten_api

logger = logging.getLogger(__name__)

class AffiliateLinkerTask(BaseTaskModule):
    """
    Adds an affiliate link section (from Rakuten) to the article content.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = GeminiService()

    def _extract_affiliate_keywords(self, title: str, content: str, blog_info: Dict[str, Any]) -> List[str]:
        try:
            blog_name = blog_info.get('blog_name', '')
            blog_description = blog_info.get('description', '')
            
            prompt = f"""ブログ記事から商品検索キーワードを3-5個抽出してください。

【ブログ情報】
名前: {blog_name}
コンセプト: {blog_description}

【記事タイトル】
{title}

【本文（冒頭）】
{content[:500]}

JSON形式 {{"keywords": ["キーワード1", "キーワード2"]}} で出力してください。"""
            
            response = self.llm_service.generate_text(prompt)
            if not response: return []
            
            clean_response = re.sub(r'```json\s*|```\s*', '', response).strip()
            result = json.loads(clean_response)
            return result.get('keywords', [])[:5]
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title = inputs.get("title")
        content = inputs.get("content")
        article_concept = inputs.get("article_concept", {})
        blog_info = inputs.get("blog") or {}

        if not title or not content:
            raise ValueError("Title and content are required.")

        if not self.config.get('enabled', True):
            return {"enhanced_content": content}

        try:
            keywords = self._extract_affiliate_keywords(title, content, blog_info)
            if not keywords: return {"enhanced_content": content}

            products = rakuten_api.search_related_products(article_concept, keywords, gemini_service=self.llm_service)
            if not products: return {"enhanced_content": content}

            section = "\n\n## 🛒 おすすめ関連商品\n\n"
            for i, product in enumerate(products[:3], 1):
                name = product.get('itemName', '商品')
                price = product.get('itemPrice', 0)
                url = product.get('affiliate_url', product.get('itemUrl', ''))
                img = product.get('imageUrl', '')
                section += f"### {i}. {name}\n\n"
                if img: section += f"[![{name}]({img})]({url})\n\n"
                section += f"**価格**: ¥{price:,}\n\n[詳細を見る]({url})\n\n---\n\n"

            return {"enhanced_content": content + section}
        except Exception as e:
            logger.error(f"Affiliate linker failed: {e}")
            return {"enhanced_content": content}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "AffiliateLinkerTask"}
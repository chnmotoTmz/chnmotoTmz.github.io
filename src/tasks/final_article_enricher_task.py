import re
import json
import logging
import requests
import time
from typing import Dict, Any, List, Optional

from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService
from src.services import rakuten_api

logger = logging.getLogger(__name__)

class FinalArticleEnricherTask(BaseTaskModule):
    """
    Final stage article enrichment:
    1. Performs DuckDuckGo search for fact-checking references.
    2. Fetches Rakuten affiliate products.
    3. Fetches past articles (similar articles).
    4. Merges them into the final content using a PURE CODE GENERATION strategy (No AI for formatting).
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = GeminiService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title = inputs.get("final_title") or inputs.get("title") or inputs.get("base_title")
        content = inputs.get("final_content") or inputs.get("content") or inputs.get("content_with_links")
        article_concept = inputs.get("article_concept", {})
        similar_articles = inputs.get("similar_articles", [])
        
        if not content:
            logger.error("No content found to enrich.")
            return inputs

        # --- Scavenger Protocol: Search and Destroy AI Duplicates ---
        logger.info("Stripping potential AI-generated placeholders.")
        patterns_to_strip = [
            r"##\s*📚\s*参考文献.*?(?=\n##|\n\n|$)",
            r"##\s*Reference.*?(?=\n##|\n\n|$)",
            r"##\s*🛒\s*本日のおすすめアイテム.*?(?=\n##|\n\n|$)",
            r"##\s*おすすめ商品.*?(?=\n##|\n\n|$)",
            r"##\s*🔗\s*あわせて読みたい.*?(?=\n##|\n\n|$)",
            r"🛒\s*本日のおすすめアイテム.*?(?=\n##|\n\n|$)"
        ]
        for pattern in patterns_to_strip:
            content = re.sub(pattern, "", content, flags=re.DOTALL | re.IGNORECASE).strip()

        keywords = article_concept.get("keywords", [])
        if not keywords:
            keywords = [title] if title else ["ブログ記事"]

        logger.info(f"--- Final Enrichment Phase (Code-Only Strategy) ---")

        # 1. Fact Check Section (Code-generated)
        fact_check_html = self._get_fact_check_html(keywords[:2])

        # 2. Past Articles Section (Code-generated)
        past_articles_html = self._get_past_articles_html(similar_articles)

        # 3. Affiliate Section (Code-generated)
        affiliate_html = self._get_affiliate_html(article_concept, keywords[:3])

        # 4. Final Physical Merge
        enriched_content = content.strip()
        
        if fact_check_html:
            enriched_content += "\n\n<hr/>\n\n## 📚 参考文献\n\n" + fact_check_html
            
        if past_articles_html:
            enriched_content += "\n\n## 🔗 あわせて読みたい\n\n" + past_articles_html

        if affiliate_html:
            enriched_content += "\n\n## 🛒 おすすめ商品\n\n" + affiliate_html

        return {
            "final_title": title,
            "final_content": enriched_content
        }

    def _get_fact_check_html(self, keywords: List[str]) -> str:
        all_results = []
        for kw in keywords:
            results = self._search_duckduckgo(kw)
            all_results.extend(results)
            if len(all_results) >= 3: break
        
        if not all_results: return ""

        html = "<ul>\n"
        for res in all_results[:3]:
            # Physical URL adoption - No AI mangling
            html += f"  <li><a href='{res['url']}'>{res['title']}</a></li>\n"
        html += "</ul>"
        return html

    def _get_affiliate_html(self, concept: Dict, keywords: List[str]) -> str:
        try:
            products = rakuten_api.search_related_products(concept, keywords)
            if not products: return ""

            # Pure code-generated layout for reliability
            html = "<div class='rakuten-items' style='display:flex; flex-direction:column; gap:20px;'>\n"
            for p in products[:3]:
                name = p.get('itemName', '商品')
                price = p.get('itemPrice', 0)
                url = p.get('affiliate_url')
                img = p.get('imageUrl')
                
                html += f"  <div class='item' style='border:1px solid #eee; padding:10px; border-radius:8px;'>\n"
                if img:
                    html += f"    <a href='{url}'><img src='{img}' alt='{name}' style='float:left; margin-right:10px; max-width:100px;'/></a>\n"
                html += f"    <div style='overflow:hidden;'>\n"
                html += f"      <a href='{url}' style='font-weight:bold; text-decoration:none;'>{name}</a><br/>\n"
                html += f"      <span style='color:#c00; font-size:1.1em;'>価格: ¥{price:,}</span><br/>\n"
                html += f"      <a href='{url}' style='display:inline-block; margin-top:5px; padding:5px 10px; background:#c00; color:#fff; border-radius:4px; text-decoration:none;'>楽天で見る</a>\n"
                html += f"    </div>\n"
                html += f"    <div style='clear:both;'></div>\n"
                html += f"  </div>\n"
            html += "</div>"
            return html
        except Exception as e:
            logger.warning(f"Affiliate logic failed: {e}")
            return ""

    def _get_past_articles_html(self, articles: List[Dict]) -> str:
        if not articles: return ""
        
        html = "<ul>\n"
        for art in articles[:3]:
            # Physical URL adoption
            html += f"  <li><a href='{art.get('url')}'>{art.get('title')}</a></li>\n"
        html += "</ul>"
        return html

    def _search_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        try:
            url = "https://duckduckgo.com/html/"
            params = {"q": query}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200: return []
            results = []
            matches = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', resp.text)
            for link, title in matches[:3]:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                if 'duckduckgo.com' in link: continue
                results.append({"title": clean_title, "url": link})
            return results
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "FinalArticleEnricher",
            "description": "PURE CODE physical merging of search, affiliate, and RAG links."
        }
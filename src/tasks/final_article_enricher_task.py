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

        # Capture any existing affiliate block BEFORE we strip placeholders so we can restore it
        original_affiliate_block = None
        try:
            affiliate_block_regex = r"(##\s*(?:🛒\s*)?(?:おすすめ商品|本日のおすすめアイテム|本日のおすすめ|おすすめ).*?(?=\n##|\n\n|$))"
            m = re.search(affiliate_block_regex, content, flags=re.DOTALL | re.IGNORECASE)
            if m:
                original_affiliate_block = m.group(0).strip()
        except Exception:
            original_affiliate_block = None

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

        # 3. Affiliate Section: perform a single Rakuten query and decide how to proceed
        try:
            products = rakuten_api.search_related_products(article_concept, keywords[:3])
        except Exception as e:
            logger.warning(f"Rakuten products search failed: {e}")
            products = []

        affiliate_md = ""
        affiliate_html = ""
        affiliate_status = "none"

        if products:
            affiliate_md = self._render_affiliate_markdown_from_products(products)
            affiliate_html = self._render_affiliate_html_from_products(products)
            affiliate_status = "found"
        else:
            if original_affiliate_block:
                # Restore original user-provided affiliate block
                affiliate_html = None
                affiliate_md = None
                affiliate_restore_block = original_affiliate_block
                affiliate_status = "restored_original"
            else:
                # Insert a small placeholder and log the failure for observability
                affiliate_placeholder = "\n\n## 🛒 おすすめ商品\n\n現在こちらのカテゴリーで利用可能なアフィリエイト商品が見つかりませんでした。後で再検索します。"
                affiliate_restore_block = affiliate_placeholder
                affiliate_status = "placeholder_inserted"

                try:
                    log_entry = {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "blog": inputs.get("blog_data", {}).get("hatena_blog_id"),
                        "reason": "no_rakuten_products",
                        "action": affiliate_status
                    }
                    with open("logs/affiliate_failures.log", "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                except Exception as e:
                    logger.warning(f"Failed to write affiliate failure log: {e}")

        # 4. Final Physical Merge
        enriched_content = content.strip()
        
        if fact_check_html:
            enriched_content += "\n\n<hr/>\n\n## 📚 参考文献\n\n" + fact_check_html
            
        if past_articles_html:
            enriched_content += "\n\n## 🔗 あわせて読みたい\n\n" + past_articles_html

        # Prefer markdown-style affiliate block (Hatena-friendly). Fall back to HTML if markdown unavailable.
        if affiliate_status == "found":
            if affiliate_md:
                enriched_content += "\n\n## 🛒 おすすめ商品\n\n" + affiliate_md
            elif affiliate_html:
                enriched_content += "\n\n## 🛒 おすすめ商品\n\n" + affiliate_html
        else:
            # restored_original or placeholder_inserted
            enriched_content += "\n\n" + affiliate_restore_block

        return {
            "final_title": title,
            "final_content": enriched_content,
            "affiliate_status": affiliate_status
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

    def _get_affiliate_markdown(self, concept: Dict, keywords: List[str]) -> str:
        """Generate a markdown-formatted affiliate block similar to the user's example.

        Each item will be formatted as:
        [![Title](image_url)](affiliate_url)

        **[Title](affiliate_url)**
        価格: ¥xxx
        """
        try:
            products = rakuten_api.search_related_products(concept, keywords)
            if not products: return ""

            lines: List[str] = []
            for p in products[:5]:
                name = p.get('itemName') or '商品'
                price = p.get('itemPrice')
                price_str = f"¥{price:,}" if price is not None else ""
                url = p.get('affiliate_url') or p.get('itemUrl') or '#'
                img = p.get('imageUrl') or ''

                if img:
                    lines.append(f"[![{name}]({img})]({url})")
                else:
                    # Fallback small spacer or empty line to keep spacing
                    lines.append(f"[![{name}](https://via.placeholder.com/128)]({url})")

                lines.append("")
                lines.append(f"**[{name}]({url})**")
                if price_str:
                    lines.append(f"価格: {price_str}")
                lines.append("")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Affiliate markdown generation failed: {e}")
            return ""

    def _render_affiliate_html_from_products(self, products: List[Dict]) -> str:
        """Render HTML affiliate block directly from products list (no API calls)."""
        if not products: return ""
        html = "<div class='rakuten-items' style='display:flex; flex-direction:column; gap:20px;'>\n"
        for p in products[:3]:
            name = p.get('itemName', '商品')
            price = p.get('itemPrice', 0)
            url = p.get('affiliate_url') or p.get('itemUrl') or '#'
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

    def _render_affiliate_markdown_from_products(self, products: List[Dict]) -> str:
        """Render markdown affiliate block directly from products list (no API calls)."""
        if not products: return ""
        lines: List[str] = []
        for p in products[:5]:
            name = p.get('itemName') or '商品'
            price = p.get('itemPrice')
            price_str = f"¥{price:,}" if price is not None else ""
            url = p.get('affiliate_url') or p.get('itemUrl') or '#'
            img = p.get('imageUrl') or ''

            if img:
                lines.append(f"[![{name}]({img})]({url})")
            else:
                lines.append(f"[![{name}](https://via.placeholder.com/128)]({url})")

            lines.append("")
            lines.append(f"**[{name}]({url})**")
            if price_str:
                lines.append(f"価格: {price_str}")
            lines.append("")

        return "\n".join(lines)

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
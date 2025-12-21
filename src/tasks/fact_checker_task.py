import re
import json
import logging
from typing import Dict, Any, List

from src.framework.base_task import BaseTaskModule
from src.services.search_service import SearchService
from src.services.gemini_service import GeminiService

class FactCheckerTask(BaseTaskModule):
    """Adds a fact-check section with reference articles to the content.

    This task inspects the article content and appends or inlines reference
    links from provided web summaries. It is robust to missing inputs and
    focuses on inserting helpful reference titles/URLs where relevant.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initializes the task with dependent services."""
        super().__init__(config)
        self.search_service = SearchService()
        self.gemini_service = GeminiService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process content and insert reference titles/URLs from web_summaries.

        Args:
            inputs (Dict[str, Any]):
                - title: article title
                - content: article content
                - web_summaries: list of dicts with keys 'url' and 'title' (optional)

        Returns:
            Dict[str, Any]: {"enhanced_content": ...}
        """
        import re
        import logging
        title: str = inputs.get("title")
        content: str = inputs.get("content")
        web_summaries = inputs.get("web_summaries", [])

        # 1. 既存�Eサムネイルを抽出�E�保存！E        thumbnail_match = re.match(r"^\s*(!\[.*?\]\(http.*?\)\n*)", content)
        thumbnail_md = thumbnail_match.group(1) if thumbnail_match else ""
        content_no_thumb = content[len(thumbnail_md):] if thumbnail_md else content

        logger = logging.getLogger("FactCheckerTask")
        try:
            logger.debug(f"[FactCheckerTask] title: {title}")
            logger.debug(f"[FactCheckerTask] content: {content[:200]}...")
            
            # content_no_thumb を対象に処琁E            content_to_process = content_no_thumb

            if not title or not content_to_process:
                logger.error("Title and content are required inputs.")
                raise ValueError("Title and content are required inputs.")

            # web_summariesをURL→title辞書に変換
            url2title = {}
            for ws in web_summaries:
                url = ws.get("url")
                t = ws.get("title")
                if url and t:
                    url2title[url] = t

            # Extract Markdown links and raw URLs
            def find_links(text):
                # Markdown links: [text](url) but ignore image links ![alt](url)
                md_links = re.findall(r'(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)\)', text)
                # Raw URLs: https://...  (exclude URLs already present in Markdown links)
                used_urls = set(u for _, u in md_links)
                raw_urls = set(re.findall(r'(https?://[\w\-\./%#?=&;:_~]+)', text)) - used_urls
                return list(md_links), list(raw_urls)
            
            # 補足挿入対象外�EURLパターン
            def should_skip_url(url):
                skip_patterns = [
                    'imgur.com', 'i.imgur.com', 'rakuten.co.jp', 'hb.afl.rakuten',
                    'thumbnail.image.rakuten', 'amazon.co.jp', 'amzn.to',
                    '.jpg', '.jpeg', '.png', '.gif', '.webp',
                ]
                url_lower = url.lower()
                return any(p in url_lower for p in skip_patterns)

            md_links, raw_urls = find_links(content_to_process)

            # Helper to create a small reference note for a URL
            def make_note(url):
                t = url2title.get(url)
                if t:
                    return f"（参照: {t}）"
                return f"（参照: {url}）"

            # Markdownリンク直後に補足挿入
            new_content = content_to_process
            for link_text, url in md_links:
                if should_skip_url(url): continue
                note = make_note(url)
                pat = re.escape(f'[{link_text}]({url})')
                if not re.search(pat + re.escape(note), new_content):
                    new_content = re.sub(pat, f'[{link_text}]({url}){note}', new_content)

            # 生URLにも補足挿入
            for url in raw_urls:
                if should_skip_url(url): continue
                note = make_note(url)
                pat = re.escape(url)
                if not re.search(pat + re.escape(note), new_content):
                    new_content = re.sub(pat, f'{url}{note}', new_content)

            return {"enhanced_content": thumbnail_md + new_content}
        except Exception as e:
            logger.error(f"[FactCheckerTask] Exception: {e}", exc_info=True)
            return {"enhanced_content": content}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "FactChecker",
            "description": "Adds fact-check inline references to the article content.",
            "inputs": { "title": "str", "content": "str" },
            "outputs": { "enhanced_content": "str" }
        }

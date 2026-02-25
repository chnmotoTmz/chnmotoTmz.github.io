"""
参考リンク・関連記事のリンク修復モジュール。
AIが生成したプレースホルダーリンク (#, example.com等) を
DuckDuckGoで検索して実際のURLに置き換える。
"""
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


def search_duckduckgo(query: str) -> Optional[str]:
    """DuckDuckGo HTML版で検索し、最初の結果URLを返す。"""
    try:
        resp = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=8
        )
        if resp.status_code == 200:
            # DuckDuckGo result link pattern
            matches = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', resp.text)
            for raw_url in matches:
                # DuckDuckGo wraps URLs in a redirect
                from urllib.parse import unquote, urlparse, parse_qs
                parsed = urlparse(raw_url)
                qs = parse_qs(parsed.query)
                # Extract actual URL from redirect params
                if 'uddg' in qs:
                    url = unquote(qs['uddg'][0])
                elif 'u' in qs:
                    url = unquote(qs['u'][0])
                else:
                    url = unquote(raw_url)
                
                # Skip tracker/ad URLs
                if 'duckduckgo.com' in url or 'bing.com' in url:
                    continue
                if url.startswith('http'):
                    return url
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed for '{query}': {e}")
    return None


def cleanup_fact_references(title: str, content: str) -> str:
    """
    記事内の死んだリンク（#, example.com など）を検出し、
    リンクテキストをキーワードにDuckDuckGo検索して実URLに置き換える。
    
    対応パターン:
    - [テキスト](#)
    - [テキスト](https://example.com)
    - [テキスト](TempURL)
    - Ref: テキスト（URLなし）
    """
    # Pattern: Markdown link with dead URL (#, example.com, TempURL, empty)
    dead_link_pattern = re.compile(
        r'\[([^\]]+)\]\((#|https?://(?:www\.)?example\.com[^\)]*|TempURL[^\)]*|)\)'
    )
    
    def replace_dead_link(match):
        link_text = match.group(1).strip()
        if not link_text:
            return match.group(0)  # empty text, skip
        
        # Search with article title context for better results
        search_query = f"{link_text}"
        url = search_duckduckgo(search_query)
        
        if url:
            logger.info(f"Resolved: [{link_text}] -> {url}")
            return f"[{link_text}]({url})"
        else:
            # Couldn't resolve — remove the dead link, keep as plain text
            logger.warning(f"Could not resolve link: [{link_text}]")
            return link_text
    
    # Replace all dead links
    result = dead_link_pattern.sub(replace_dead_link, content)
    
    # Also handle the old-style 📚 Reference / Ref: format
    ref_pattern = re.compile(r'^Ref:\s*(.+)$', re.MULTILINE)
    def replace_ref(match):
        ref_title = match.group(1).strip()
        url = search_duckduckgo(ref_title)
        if url:
            return f"- [{ref_title}]({url})"
        return f"- {ref_title}"
    
    result = ref_pattern.sub(replace_ref, result)
    
    return result

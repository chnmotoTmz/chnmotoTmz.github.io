import logging
import re
from typing import Dict, Any, List
from src.services.blog_rag_service import blog_rag_service
from src.services.hatena_blog_content_fetcher import fetch_article_content
from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)


class ParagraphExtractorTask(BaseTaskModule):
    """
    最新記事からキーワードを含む段落を抽出するタスク。
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        blog = inputs.get('blog')
        if not blog:
            raise ValueError("Input 'blog' is required.")

        search_keywords = inputs.get('search_keywords', [])
        if not search_keywords:
            logger.warning("No search_keywords provided. Task will return empty results.")
            return {"extracted_paragraphs": [], "output_file": None}

        max_articles = inputs.get('max_articles', 10)
        output_file = inputs.get('output_file', 'extracted_paragraphs.md')

        hatena_id = blog.get('hatena_id')
        blog_id = blog.get('hatena_blog_id')
        api_key = blog.get('hatena_api_key') or blog.get('api_key')

        if not all([hatena_id, blog_id, api_key]):
            raise ValueError("Blog configuration is incomplete (hatena_id, blog_id, api_key).")

        # 最新記事の一覧を取得
        logger.info(f"Fetching latest {max_articles} articles from {blog_id}...")
        entries = blog_rag_service.fetch_hatena_blog_entries(
            blog_id=blog_id,
            api_key=api_key,
            hatena_id=hatena_id
        )

        entries = entries[:max_articles]
        results = []

        for entry in entries:
            url = entry.get('url')
            title = entry.get('title')
            if not url:
                continue

            logger.info(f"Fetching content for: {title}")
            content = fetch_article_content(url)
            if not content:
                continue

            # 段落に分割（ダブル改行を区切りとする）
            paragraphs = re.split(r'\n\n+', content)
            
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                
                # キーワードが含まれているかチェック
                if any(keyword in p for keyword in search_keywords):
                    results.append({
                        "title": title,
                        "url": url,
                        "paragraph": p
                    })

        # Markdownファイルに保存
        if results:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Extracted Paragraphs\n\n")
                f.write(f"Keywords: {', '.join(search_keywords)}\n\n")
                for item in results:
                    f.write(f"## {item['title']}\n")
                    f.write(f"URL: {item['url']}\n\n")
                    f.write(f"{item['paragraph']}\n\n")
                    f.write("---\n\n")
            
            logger.info(f"Successfully saved {len(results)} paragraphs to {output_file}")
        else:
            logger.info("No paragraphs found with the given keywords.")

        return {
            "extracted_count": len(results),
            "output_file": output_file if results else None,
            "results": results
        }

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "ParagraphExtractor",
            "description": "Extracts paragraphs containing keywords from latest articles."
        }
"""
RAG Similar Articles Fetcher Task

ユーザーの入力と記事コンセプトに基づき、RAGモデルから類似記事を検索します。
検索結果は、記事生成時のコンテキストとして使用されます。
"""

import logging
import re
from typing import Dict, Any, List, Optional
from src.services.blog_rag_service import blog_rag_service
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class RagSimilarArticlesFetcher(BaseTaskModule):
    """RAGモデルから類似記事を取得するタスク"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = GeminiService()
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        類似記事を検索し、コンテキスト情報を返します。
        """
        try:
            texts = inputs.get('texts', [])
            article_concept = inputs.get('article_concept', '')
            blog_data = inputs.get('blog', {})
            
            if not blog_data:
                logger.warning("Blog data not found. Skipping RAG search.")
                return self._empty_result()
            
            blog_id = blog_data.get('hatena_blog_id')
            if not blog_id:
                logger.warning("hatena_blog_id not found. Skipping RAG search.")
                return self._empty_result()
            
            # 検索クエリを構築
            query = self._build_search_query(texts, article_concept)
            logger.info(f"RAG Search Query: {query[:100]}...")
            
            # RAGモデルから類似記事を検索
            results = blog_rag_service.search_similar_entries(
                blog_id=blog_id,
                query=query,
                top_k=5
            )
            
            if not results:
                logger.info(f"No similar articles found for blog '{blog_id}'.")
                return self._empty_result()
            
            # 結果をフォーマット（サマリー付き）
            similar_articles = []
            for result in results:
                content = result.get('content', '')
                similar_articles.append({
                    'title': result.get('title', '無題'),
                    'url': result.get('url', ''),
                    'content': content[:800],
                    'summary': self._generate_article_summary(result.get('title', ''), content),
                    'score': result.get('score', 0.0)
                })
            
            writing_style_hints = self._extract_writing_style_hints(similar_articles)
            logger.info(f"RAG search completed. Found {len(similar_articles)} articles.")
            
            return {
                'similar_articles': similar_articles,
                'writing_style_hints': writing_style_hints
            }
            
        except Exception as e:
            logger.error(f"Error during RAG search: {e}", exc_info=True)
            return self._empty_result()
    
    def _build_search_query(self, texts: List[Any], article_concept: Any) -> str:
        """検索クエリを構築します"""
        string_texts = []
        for text in texts:
            if isinstance(text, str):
                string_texts.append(text)
            elif isinstance(text, dict):
                string_texts.append(text.get('text', '') or text.get('content', '') or str(text))
            else:
                string_texts.append(str(text))
        
        user_input = ' '.join(string_texts)
        
        concept_str = ""
        if isinstance(article_concept, dict):
            theme = article_concept.get('theme', '')
            keywords = article_concept.get('keywords', [])
            concept_str = f"{theme} {' '.join(keywords)}"
        else:
            concept_str = str(article_concept)
        
        return f"{concept_str} {user_input}".strip() or "記事"
    
    def _generate_article_summary(self, title: str, content: str) -> str:
        """LLMで記事のサマリーを生成します"""
        if not content or len(content) < 50:
            return f"「{title}」に関する記事"
        
        try:
            prompt = f"""以下の記事を100字以内で要約してください。
要点だけを簡潔に。説明不要。

【タイトル】{title}

【本文】
{content[:1500]}

【出力】
要約のみを出力（「この記事の〜」などの前置き不要）。"""

            summary = self.llm_service.generate_text(prompt, max_tokens=200)
            if summary:
                return summary.strip()[:200]
        except Exception as e:
            logger.warning(f"Summary generation error: {e}")
        
        return content[:100] + "..."
    
    def _extract_writing_style_hints(self, similar_articles: List[Dict[str, Any]]) -> str:
        """類似記事から文体のヒント繧抽出します"""
        if not similar_articles:
            return "標準的なスタイル"
        
        hints = []
        total_len = sum(len(a.get('content', '')) for a in similar_articles)
        avg_len = total_len // len(similar_articles)
        
        if avg_len > 1500: hints.append("詳細な長文記事")
        elif avg_len > 800: hints.append("中程度の記事")
        else: hints.append("簡潔な記事")
        
        sample = similar_articles[0].get('content', '')
        if 'です' in sample or 'ます' in sample:
            hints.append("ですます調")
        else:
            hints.append("である調")
            
        return "、".join(hints)
    
    def _empty_result(self) -> Dict[str, Any]:
        return {
            'similar_articles': [],
            'writing_style_hints': ''
        }
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "RagSimilarArticlesFetcher",
            "description": "Retrieves similar articles from RAG model for context enrichment.",
            "inputs": {
                "texts": "List[str]",
                "article_concept": "str",
                "blog": "Dict"
            },
            "outputs": {
                "similar_articles": "List[Dict]",
                "writing_style_hints": "str"
            }
        }

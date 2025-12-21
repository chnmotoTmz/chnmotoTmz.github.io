from typing import Dict, Any, List, Optional
import logging
import re

__all__ = ["ArticleConceptDefinerTask"]

from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class ArticleConceptDefinerTask(BaseTaskModule):
    """
    Defines the concept for the article based on input materials using LLM analysis.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = GeminiService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        texts = inputs.get("texts", [])
        blog_data = inputs.get("blog") or {}
        repost_data = inputs.get("repost_data")
        
        if texts and isinstance(texts[0], dict) and "summary" in texts[0]:
            texts = [ws.get("summary", "") for ws in texts]
        
        if repost_data:
            cached_content = repost_data.get("content", "")
            cached_title = repost_data.get("title", "")
            texts = [f"【リポスト元記事】{cached_title}\n{cached_content}"] + (texts or [])
        
        blog_name = blog_data.get("name", "") or "ブログ"
        blog_description = blog_data.get("description", "")
        
        logger.info(f"🔍 Analyzing content concept for blog '{blog_name}'")
        
        prompt = f"""ブログ記事のコンセプトを定義してください。

【ブログ情報】
名前: {blog_name}
概要: {blog_description}

【コンテンツ】
{" ".join(texts[:3])}

以下のJSON形式で出力してください：
{{
    "theme": "記事テーマ（30文字以内）",
    "genre": "ジャンル",
    "keywords": ["キーワード1", "キーワード2", "キーワード3"],
    "target_audience": "想定読者層",
    "writing_tone": "文体",
    "axes": [
        {{
            "name": "独自の切り口名",
            "description": "説明",
            "content_angle": "追加すべき補足内容"
        }}
    ]
}}
JSON以外の説明文は一切含めないこと。"""
        
        response = self.llm_service.generate_text(prompt, max_tokens=600)
        if not response:
            raise ValueError("LLM concept analysis returned empty response.")
            
        concept = self._parse_concept_response(response)
        return {
            "article_concept": concept
        }

    def _parse_concept_response(self, response: str) -> Dict[str, Any]:
        import json
        
        # Clean up the response first
        cleaned_response = response.strip()
        
        # Try to find JSON block in markdown
        match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned_response = match.group(1)
        else:
            # Try to find the first outer-most JSON object
            start = cleaned_response.find('{')
            end = cleaned_response.rfind('}')
            if start != -1 and end != -1:
                cleaned_response = cleaned_response[start:end+1]

        try:
            concept_data = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}. Response: {cleaned_response[:200]}...")
            raise ValueError(f"No JSON found in concept response: {response[:100]}...")
            
        return {
            'theme': str(concept_data.get('theme', 'ブログ記事'))[:30],
            'genre': str(concept_data.get('genre', '一般')),
            'keywords': concept_data.get('keywords', [])[:5],
            'target_audience': str(concept_data.get('target_audience', '一般読者')),
            'writing_tone': str(concept_data.get('writing_tone', '親しみやすい')),
            'axes': concept_data.get('axes', [])[:3]
        }

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "ArticleConceptDefiner",
            "description": "Defines article concept using LLM.",
            "inputs": {"texts": "List[str]", "blog": "Dict"},
            "outputs": {"article_concept": "Dict"}
        }
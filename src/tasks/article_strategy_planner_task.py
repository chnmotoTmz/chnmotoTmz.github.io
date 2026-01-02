from typing import Dict, Any, List, Optional
import logging
import json
import re

from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class ArticleStrategyPlannerTask(BaseTaskModule):
    """
    Plans the article structure and strategy before writing content.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = GeminiService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        article_concept = inputs.get("article_concept", {})
        texts = inputs.get("texts", [])
        web_summaries = inputs.get("web_summaries", [])
        blog_data = inputs.get("blog") or {}
        
        if texts and isinstance(texts[0], dict) and "summary" in texts[0]:
            texts = [ws.get("summary", "") for ws in texts]

        prompt = self._build_prompt(article_concept, texts, web_summaries, blog_data)
        
        response_text = self.llm_service.generate_text(prompt, max_tokens=1000)
        strategy = self._parse_json_response(response_text)
        
        return {
            "article_structure": strategy.get("structure", []),
            "affiliate_strategy": strategy.get("affiliate_strategy", {}),
            "thumbnail_concept": strategy.get("thumbnail_concept", "Blog image"),
            "target_keywords": strategy.get("target_keywords", []),
            "mentioned_products": self._extract_products(texts)
        }

    def _build_prompt(self, concept: Dict, texts: List[str], web_summaries: List[Dict], blog_data: Dict) -> str:
        context = "\n".join(texts[:3])
        web_info = "\n".join([f"- {w.get('title')}: {w.get('summary')}" for w in web_summaries])
        
        return f"""記事の構成案を策定してください。

【重要：入力データの取り扱い】
提供された【コンテンツ】には、システムログ、タスク実行履歴、デバッグ情報などのノイズが含まれている可能性があります。これらは無視し、記事のテーマに関連する情報のみを抽出して構成案を作成してください。

【ブログ情報】
名前: {blog_data.get('name')}
コンセプト: {concept.get('theme')}

【コンテンツ】
{context}
{web_info}

以下のJSON形式のみを出力してください：
{{
    "structure": [
        {{"heading": "見出し1", "content_points": ["ポイント1", "ポイント2"]}}
    ],
    "affiliate_strategy": {{"target_product": "推奨商品", "approach": "訴求方法"}},
    "thumbnail_concept": "サムネイル画像の説明",
    "target_keywords": ["キーワード1", "キーワード2"]
}}"""

    def _extract_products(self, texts: List[str]) -> List[str]:
        combined = " ".join(texts)
        matches = re.findall(r'(?:【|「)([^】」]+)(?:】|」)', combined)
        return list(dict.fromkeys(matches))[:5]

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return json.loads(response.strip())
        except:
            return {}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "ArticleStrategyPlanner",
            "description": "Plans article structure and strategy.",
            "inputs": {"article_concept": "Dict", "texts": "List[str]"},
            "outputs": {"article_structure": "List", "affiliate_strategy": "Dict"}
        }
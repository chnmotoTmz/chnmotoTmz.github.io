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
        images = inputs.get("images_for_prompt", [])
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
        
        # Include image descriptions in content
        content_parts = texts[:3]
        for img in images:
            desc = img.get("description")
            if desc and desc != "画像解析に失敗しました":
                content_parts.append(f"画像情報: {desc}")
        
        prompt = f"""ブログ記事のコンセプトを定義してください。

【重要：入力データの取り扱い】
提供された【コンテンツ】には、システムログ、タスク実行履歴、デバッグ情報などのノイズが含まれている可能性があります。これらは無視し、記事のテーマに関連する情報のみを抽出してコンセプトを定義してください。

【ブログ情報】
名前: {blog_name}
概要: {blog_description}

【コンテンツ】
{" ".join(content_parts)}

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
        import json, time, os
        from json import JSONDecoder

        cleaned_response = (response or '').strip()
        logger.debug("Concept response (truncated): %s", cleaned_response[:500])

        def _save_failure(resp_text: str) -> str:
            try:
                os.makedirs('logs/failed_concepts', exist_ok=True)
                ts = int(time.time() * 1000)
                path = f'logs/failed_concepts/concept_parse_fail_{ts}.txt'
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(resp_text)
                return path
            except Exception as e:
                logger.warning("Failed to write parse failure file: %s", e)
                return ''

        # 1) If there's an explicit ```json block, prefer that
        m = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL | re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
        else:
            candidate = cleaned_response

        # 2) Try JSONDecoder.raw_decode to parse initial JSON and ignore trailing text
        decoder = JSONDecoder()
        try:
            obj, idx = decoder.raw_decode(candidate)
            concept_data = obj
            logger.debug("Parsed JSON via raw_decode, consumed %d chars", idx)
        except Exception:
            # If raw_decode failed, try starting at the first '{' (handle leading prose)
            start_idx = candidate.find('{')
            if start_idx != -1:
                try:
                    obj, idx2 = decoder.raw_decode(candidate[start_idx:])
                    concept_data = obj
                    logger.debug("Parsed JSON via raw_decode after slicing leading text, consumed %d chars", idx2)
                except Exception:
                    # 3) Try to extract the first balanced { ... } substring
                    start = start_idx
                    candidate_obj = None
                    if start != -1:
                        depth = 0
                        for i in range(start, len(candidate)):
                            ch = candidate[i]
                            if ch == '{':
                                depth += 1
                            elif ch == '}':
                                depth -= 1
                                if depth == 0:
                                    candidate_obj = candidate[start:i+1]
                                    break
                    if candidate_obj:
                        try:
                            concept_data = json.loads(candidate_obj)
                            logger.debug("Parsed JSON via balanced-brace extraction")
                        except Exception:
                            concept_data = None
                    else:
                        concept_data = None
            else:
                concept_data = None

        # 4) If still None, retry LLM with strict JSON-only instruction once
        if concept_data is None:
            logger.warning("Initial JSON parsing failed - retrying LLM with strict JSON-only instruction.")
            strict_prompt = (
                "あなたは今から指定したJSONスキーマに厳密に従い、説明文を一切付けず、" 
                "純粋なJSONオブジェクトのみを出力してください。スキーマ:")
            strict_prompt += "\n" + (
                '{"theme": "...", "genre": "...", "keywords": ["...","..."], "target_audience": "...", "writing_tone": "...", "axes": [{"name":"...","description":"...","content_angle":"..."}]}'
            )
            strict_prompt += "\n元の生成応答を下に示します。これをJSON形式だけで再出力してください。\n\n原文:\n" + cleaned_response

            retry_resp = self.llm_service.generate_text(strict_prompt, max_tokens=400, temperature=0.0)
            if retry_resp:
                retry_text = retry_resp.strip()
                logger.debug("Retry response (truncated): %s", retry_text[:400])
                # try raw_decode again
                try:
                    obj, idx = decoder.raw_decode(retry_text)
                    concept_data = obj
                    logger.debug("Parsed JSON from retry via raw_decode, consumed %d chars", idx)
                except Exception:
                    # final attempt: extract balanced braces from retry
                    start = retry_text.find('{')
                    candidate_obj = None
                    if start != -1:
                        depth = 0
                        for i in range(start, len(retry_text)):
                            ch = retry_text[i]
                            if ch == '{':
                                depth += 1
                            elif ch == '}':
                                depth -= 1
                                if depth == 0:
                                    candidate_obj = retry_text[start:i+1]
                                    break
                    if candidate_obj:
                        try:
                            concept_data = json.loads(candidate_obj)
                        except Exception:
                            concept_data = None

        if concept_data is None:
            failure_path = _save_failure(response)
            logger.error("JSON parse error: could not extract JSON. Saved raw response to: %s", failure_path)
            raise ValueError(f"No JSON found in concept response. Saved raw response to: {failure_path}")

        # Build normalized result
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
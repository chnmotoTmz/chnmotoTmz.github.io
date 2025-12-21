"""QualityService wrapper around existing heuristic quality utilities.

Separates concerns so that routing / pipeline code depends on a cohesive service
rather than raw functions. This enables future replacement with ML-based evaluators
without touching upstream flow.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any

from src.quality import (
    check_input_requirements,
    evaluate_article_quality,
    enforce_emoji_limit,
    InputCheckResult,
    ArticleQualityResult,
)

@dataclass
class FinalQualityOutcome:
    title: str
    content: str
    quality: ArticleQualityResult
    passed: bool

class QualityService:
    def __init__(self, min_chars: int = 600, max_emoji_per_paragraph: int = 1, gemini_service: Any | None = None):
        self.min_chars = min_chars
        self.max_emoji_pp = max_emoji_per_paragraph
        self.gemini_service = gemini_service  # optional LLM for deeper assessments

    def check_inputs(self, messages: List[str]) -> InputCheckResult:
        return check_input_requirements(messages, min_messages=1)

    def evaluate_article(self, title: str, html: str) -> ArticleQualityResult:
        return evaluate_article_quality(title, html, min_chars=self.min_chars)

    def normalize_emojis(self, html: str) -> str:
        return enforce_emoji_limit(html, max_per_paragraph=self.max_emoji_pp)

    def final_pass(self, title: str, html: str) -> FinalQualityOutcome:
        limited = self.normalize_emojis(html)
        q = self.evaluate_article(title, limited)
        return FinalQualityOutcome(title=title, content=limited, quality=q, passed=q.pass_checks)

    # Combined heuristic + LLM style/article reference assessment
    def assess_article(self, title: str, article_html: str) -> Dict[str, Any]:
        heur = self.evaluate_article(title, article_html)
        readability = ''
        reference = ''
        if self.gemini_service:
            try:
                readability_prompt = (
                    "以下のブログ記事を読みやすさの観点で評価してください。\n"
                    "- 構成や段落、見出しは適切か\n"
                    "- 冗長な部分や分かりにくい表現はないか\n"
                    "- 文章の流れや語尾は自然か\n\n記事本文:\n" + article_html + "\n"\
                    "\n評価結果を100文字以内で要約し、必要なら修正案を提案してください。"
                )
                readability = (self.gemini_service.generate_content(readability_prompt) or '').strip()
            except Exception:
                readability = 'チェック失敗'
            try:
                reference_prompt = (
                    "以下のブログ記事に、読者のためになる参考情報（公式情報、第三者の評価、関連リンク等）が十分に含まれていますか？\n"
                    "不足している場合は、追加すべき情報やリンク例を提案してください。\n\n記事本文:\n" + article_html + "\n"\
                    "\n評価結果を100文字以内で要約し、必要なら追加案を提案してください。"
                )
                reference = (self.gemini_service.generate_content(reference_prompt) or '').strip()
            except Exception:
                reference = 'チェック失敗'
        return {
            'heuristics': heur,
            'readability': readability,
            'reference': reference,
            'overall_pass': heur.pass_checks and bool(readability) and bool(reference)
        }

__all__ = [
    'QualityService',
    'FinalQualityOutcome'
]

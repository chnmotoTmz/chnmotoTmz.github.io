"""Quality & validation utilities.

Provides:
 - 5W1H / experiential input sufficiency check before article generation
 - Article quality heuristics (title/body consistency, concreteness, length, emoji limits)

Design notes:
Heuristics are lightweight / regex based to avoid extra API calls and keep latency low.
If future ML/RAG based evaluation is added, keep the public function signatures compatible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict

W_TOKENS = ["いつ", "今日", "昨日", "先週", "今朝", "昨夜", "年", "月", "日"]
H_TOKENS = ["どのように", "方法", "工夫", "手順", "どうやって", "プロセス"]
WHY_TOKENS = ["なぜ", "理由", "ため", "目的", "背景"]
WHERE_TOKENS = ["で", "場所", "公園", "駅", "山", "川", "自宅", "カフェ", "オフィス", "市", "区", "県"]
WHO_TOKENS = ["私", "僕", "父", "母", "娘", "息子", "家族", "妻", "夫", "友人"]
WHAT_VERB_PATTERN = re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{2,}(した|して|行った|作った|試した|始めた|やった|感じた|考えた|学んだ)")

@dataclass
class InputCheckResult:
    ok: bool
    missing: List[str]
    details: Dict[str, bool]
    reason: str | None = None

def _has_token(text: str, tokens: List[str]) -> bool:
    return any(t in text for t in tokens)

def check_input_requirements(message_texts: List[str], min_messages: int = 1) -> InputCheckResult:
    """Check 5W1H + experiential evidence (first-person past action) presence."""
    joined = "\n".join(message_texts)
    norm = joined.replace("\u3000", " ")
    details = {
        'who': _has_token(norm, WHO_TOKENS),
        'when': _has_token(norm, W_TOKENS) or bool(re.search(r"\d{1,2}時|\d{1,2}月|\d{1,2}日", norm)),
        'where': _has_token(norm, WHERE_TOKENS),
        'what': bool(WHAT_VERB_PATTERN.search(norm)),
        'why': _has_token(norm, WHY_TOKENS),
        'how': _has_token(norm, H_TOKENS) or bool(re.search(r"(手順|まず|次に|そして)", norm)),
        'experiential': bool(re.search(r"(私は|僕は|してみた|やってみた|体験|経験)", norm)),
    }
    missing = [k for k, v in details.items() if not v and k != 'experiential']
    if len(message_texts) < min_messages:
        return InputCheckResult(False, missing, details, reason="メッセージ数不足")
    if details['experiential'] is False:
        return InputCheckResult(False, missing, details, reason="体験談が含まれていません")
    w_present = sum(int(details[k]) for k in ['who', 'when', 'where', 'what', 'why', 'how'])
    if w_present < 4:
        return InputCheckResult(False, missing, details, reason="5W1H情報が不足")
    return InputCheckResult(True, missing, details)

@dataclass
class ArticleQualityResult:
    pass_checks: bool
    issues: List[str]
    metrics: Dict[str, float]

EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]")

def evaluate_article_quality(title: str, body_html: str, min_chars: int = 500) -> ArticleQualityResult:
    text = re.sub(r"<[^>]+>", "", body_html)
    stripped = text.strip()
    length = len(stripped)
    unique_chars = len(set(stripped)) or 1
    emoji_count = len(EMOJI_PATTERN.findall(body_html))
    paragraphs = [p for p in re.split(r"\n+", stripped) if p.strip()]
    avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
    issues: List[str] = []
    if length < min_chars:
        issues.append(f"本文が短すぎます({length}文字 < {min_chars})")
    if emoji_count > max(4, length // 400):
        issues.append(f"絵文字が多すぎます({emoji_count}個)")
    if 'を目指' in title or 'を目指' in stripped:
        issues.append("『〜を目指します』形式の宣言的表現が含まれています")
    if re.search(r"(します。){2,}", stripped):
        issues.append("同一語尾『〜します。』の連続使用")
    if not re.search(r"\d", stripped):
        issues.append("数字（具体的量/日時）が本文に不足")
    if len(title) < 8 or len(title) > 60:
        issues.append("タイトル長が不適切(8〜60文字推奨)")
    title_keywords = [w for w in re.split(r"[\s、。・/|]+", title) if len(w) > 1]
    missing_title_words = [w for w in title_keywords[:3] if w and w not in stripped]
    if missing_title_words:
        issues.append(f"タイトル語句が本文に未出: {', '.join(missing_title_words)}")
    metrics = {
        'length': length,
        'unique_char_ratio': unique_chars / (length or 1),
        'emoji_count': emoji_count,
        'paragraphs': len(paragraphs),
        'avg_paragraph_length': avg_para_len,
    }
    pass_checks = len(issues) == 0
    return ArticleQualityResult(pass_checks, issues, metrics)

def enforce_emoji_limit(body_html: str, max_per_paragraph: int = 1) -> str:
    parts = body_html.split('\n')
    new_parts = []
    for part in parts:
        emojis = EMOJI_PATTERN.findall(part)
        if len(emojis) > max_per_paragraph:
            keep = emojis[:max_per_paragraph]
            no_emoji = EMOJI_PATTERN.sub('', part).rstrip()
            part = no_emoji + (keep[0] if keep else '')
        new_parts.append(part)
    return '\n'.join(new_parts)

__all__ = [
    'check_input_requirements',
    'evaluate_article_quality',
    'enforce_emoji_limit',
    'InputCheckResult',
    'ArticleQualityResult'
]

"""
Style Memory Builder Task

Analyzes writing patterns from past articles to create a style profile.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)


class StyleMemoryBuilderTask(BaseTaskModule):
    """
    Extracts style profile from past articles.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tone_markers = {
            'casual': ['〜ですよ', 'かな', 'かもしれません', '感じで', 'ちゃう'],
            'formal': ['である', 'いたします', '申し上げます', 'します'],
            'friendly': ['〜してみて', '〜してみます', 'いいですね', '気持ちいい', 'いい感じ'],
            'analytical': ['分析する', '考察する', '検証する', '調査', 'データ'],
            'narrative': ['その時', 'あの日', 'ふと思った', 'なぜか', 'ふと'],
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            similar_articles = inputs.get('similar_articles', [])
            
            if not similar_articles:
                return self._default_profile()
            
            style_profile = self._analyze_style(similar_articles)
            style_hints_text = self._generate_style_hints_text(style_profile)
            
            return {
                'style_profile': style_profile,
                'style_hints_text': style_hints_text
            }
            
        except Exception as e:
            logger.error(f"Style analysis failed: {e}", exc_info=True)
            return self._default_profile()
    
    def _analyze_style(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        tone_scores = {tone: 0 for tone in self.tone_markers.keys()}
        sentence_lengths = []
        all_markers = []
        structure_patterns = []
        
        valid_count = 0
        for article in articles[:5]:
            content = self._extract_content(article)
            if not content or len(content) < 100: continue
            
            valid_count += 1
            for tone, markers in self.tone_markers.items():
                tone_scores[tone] += sum(content.count(m) for m in markers)
            
            sentences = re.split(r'[。！\n]', content)
            sentence_lengths.extend([len(s.strip()) for s in sentences if s.strip()])
            
            structure = self._detect_structure_pattern(content)
            if structure: structure_patterns.append(structure)
            
            all_markers.extend(self._detect_markers(content))
        
        if valid_count == 0: return self._default_profile()
        
        detected_tone = max(tone_scores.items(), key=lambda x: x[1])[0]
        avg_len = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 30
        
        return {
            'tone': detected_tone,
            'tone_markers': list(set(all_markers))[:10],
            'avg_sentence_length': round(avg_len, 1),
            'structure_pattern': max(structure_patterns, key=structure_patterns.count) if structure_patterns else "standard",
            'confidence': 0.8
        }
    
    def _extract_content(self, article: Any) -> str:
        if isinstance(article, str): return article
        for field in ['content', 'text', 'body']:
            if field in article: return article[field]
        return ""
    
    def _detect_structure_pattern(self, content: str) -> str:
        if re.search(r'^(はじめに|今回)', content[:200]): return "introduction_body_conclusion"
        if re.search(r'[①1]\.', content): return "numbered_list"
        return "standard"
    
    def _detect_markers(self, content: str) -> List[str]:
        found = []
        for markers in self.tone_markers.values():
            found.extend([m for m in markers if m in content])
        return list(set(found))
    
    def _generate_style_hints_text(self, profile: Dict[str, Any]) -> str:
        desc = profile.get('tone', 'friendly')
        avg = profile.get('avg_sentence_length', 30)
        hints = f"""【文体ガイド】
- トーン: {desc}
- 平均文長: 約{avg:.0f}文字
- 構成: {profile.get('structure_pattern')}

【推奨される書き方】
1. 文体を「{desc}」で朝一する。
2. 一文を約{avg:.0f}文字程度に堅える。
"""
        return hints.strip()
    
    def _default_profile(self) -> Dict[str, Any]:
        return {
            'style_profile': {'tone': 'friendly'},
            'style_hints_text': "標準的なスタイルで書いてください。"
        }
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "StyleMemoryBuilder", "description": "Extracts style profile from past articles."}
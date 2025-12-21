"""
ローカルLLM対応コンテンツ生成エンハンサー

Gemini と ローカルLLM の両方でブログ記事を生成可能。
LLM_PROVIDER環境変数で自動切り替え。
"""

import logging
import os
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ContentEnhancerLLMUnified:
    """
    統合LLM（Gemini/ローカル）を使用したコンテンツ生成エンハンサー。
    """

    def __init__(self, blog_config: Optional[Dict[str, Any]] = None):
        """
        初期化（自動的に最適なLLMプロバイダーを選択）。

        Args:
            blog_config: ブログ設定
        """
        self.blog_config = blog_config or {}
        
        # 統合LLMファサード初期化
        from src.services.unified_llm_facade import UnifiedLLMFacade
        self.llm = UnifiedLLMFacade(blog_config=blog_config)
        
        logger.info(
            f"ContentEnhancerLLMUnified initialized with "
            f"provider: {self.llm.provider.value}"
        )

    def generate_article(
        self,
        topic: str,
        texts: List[str],
        images: List[str],
        blog_data: Dict[str, Any],
        article_concept: Dict[str, Any],
        writing_style_hints: str = "",
        similar_articles: List[Dict] = None,
        web_summaries: List[Dict] = None,
    ) -> Dict[str, Any]:
        """
        完全なブログ記事を生成。

        Args:
            topic: 記事トピック
            texts: 参考テキスト
            images: 画像パス
            blog_data: ブログ設定
            article_concept: 記事コンセプト
            writing_style_hints: 執筆スタイルヒント
            similar_articles: 類似記事
            web_summaries: Web要約

        Returns:
            {
                "title": str,
                "content": str,
                "thumbnail_prompt": str
            }
        """
        similar_articles = similar_articles or []
        web_summaries = web_summaries or []

        # テキスト整形
        if texts and isinstance(texts[0], dict) and "summary" in texts[0]:
            texts = [ws.get("summary", "") for ws in texts]

        # プロンプト構築
        system_prompt = self._build_system_prompt(blog_data)
        user_prompt = self._build_generation_prompt(
            topic=topic,
            texts=texts,
            blog_data=blog_data,
            article_concept=article_concept,
            writing_style_hints=writing_style_hints,
            similar_articles=similar_articles,
            web_summaries=web_summaries,
        )

        # LLMで生成
        logger.info(f"Generating article with {self.llm.provider.value} LLM")
        
        response = self.llm.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=3000,
        )

        # レスポンス解析
        return self._parse_article_response(response)

    def revise_article(
        self,
        title: str,
        content: str,
        feedback: str,
        blog_data: Dict[str, Any],
        concept: str = "",
    ) -> Dict[str, Any]:
        """
        記事を修正。

        Args:
            title: 記事タイトル
            content: 記事本文
            feedback: 修正フィードバック
            blog_data: ブログ設定
            concept: 記事コンセプト

        Returns:
            { "title": str, "content": str }
        """
        system_prompt = self._build_revision_system_prompt(blog_data)
        user_prompt = self._build_revision_prompt(
            title=title,
            content=content,
            feedback=feedback,
            concept=concept,
        )

        logger.info(
            f"Revising article with {self.llm.provider.value} LLM"
        )

        response = self.llm.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.5,  # 修正は保守的に
            max_tokens=3000,
        )

        return self._parse_revision_response(response)

    def analyze_image(
        self,
        image_path: str,
        context: str = "",
    ) -> str:
        """
        画像を解析。

        Args:
            image_path: 画像ファイルパス
            context: 追加コンテキスト

        Returns:
            解析結果
        """
        prompt = f"この画像について、ブログ記事の参考情報として説明してください。\n"
        if context:
            prompt += f"コンテキスト: {context}\n"
        prompt += "簡潔に、要点を箇条書きで返してください。"

        try:
            return self.llm.analyze_image_from_path(
                image_path=image_path,
                prompt=prompt,
            )
        except Exception as e:
            logger.warning(f"Image analysis failed: {e}")
            return ""

    # ======== プロンプト構築ヘルパー ========

    def _build_system_prompt(self, blog_data: Dict[str, Any]) -> str:
        """記事生成用システムプロンプト"""
        blog_name = blog_data.get("blog_name", "ブログ")
        blog_concept = blog_data.get("blog_concept", "")
        target_audience = blog_data.get("target_audience", "一般読者")

        prompt = f"""あなたは「{blog_name}」の執筆者です。

**ブログコンセプト**: {blog_concept or "なし"}
**ターゲット読者**: {target_audience}

以下の要件を満たす記事を執筆してください：

1. **読みやすさ**: 段落は3〜4行で分ける
2. **構成**: 導入 → 本論 → 結論
3. **Markdown形式**: #で見出し、**で強調、>で引用
4. **実用性**: 読者にとって実用的な情報を提供
5. **トーン**: ブログのコンセプトに合わせた トーン

記事はMarkdown形式で、以下の構成で返してください：
---
# [タイトル]

## [見出し1]
本文...

## [見出し2]
本文...

---
"""
        return prompt

    def _build_generation_prompt(
        self,
        topic: str,
        texts: List[str],
        blog_data: Dict[str, Any],
        article_concept: Dict[str, Any],
        writing_style_hints: str,
        similar_articles: List[Dict],
        web_summaries: List[Dict],
    ) -> str:
        """記事生成用ユーザープロンプト"""
        prompt = f"**トピック**: {topic}\n\n"

        if article_concept:
            concept_text = article_concept.get("concept", "")
            prompt += f"**記事コンセプト**: {concept_text}\n\n"

        if texts:
            prompt += "**参考情報**:\n"
            for i, text in enumerate(texts[:3], 1):  # 最初の3つまで
                prompt += f"- {text[:200]}...\n"
            prompt += "\n"

        if web_summaries:
            prompt += "**Web参考リンク**:\n"
            for summary in web_summaries[:3]:
                url = summary.get("url", "")
                title = summary.get("title", "")
                prompt += f"- [{title}]({url})\n"
            prompt += "\n"

        if similar_articles:
            prompt += "**類似記事の構成**:\n"
            for article in similar_articles[:2]:
                prompt += f"- {article.get('title', '')}\n"
            prompt += "\n"

        if writing_style_hints:
            prompt += f"**執筆スタイル**: {writing_style_hints}\n\n"

        prompt += "これらの情報を参考に、上記トピックについて ブログ記事を執筆してください。\n"
        prompt += "1500〜2000字程度、Markdown形式で。\n"

        return prompt

    def _build_revision_system_prompt(
        self, blog_data: Dict[str, Any]
    ) -> str:
        """修正用システムプロンプト"""
        blog_name = blog_data.get("blog_name", "ブログ")

        return f"""あなたは「{blog_name}」の編集者です。

与えられた記事を以下の観点から修正してください：

1. **文法**: 句読点、敬語、表記ゆれを統一
2. **読みやすさ**: 長い文を短く、難しい表現を簡潔に
3. **内容**: 重複を排除、論理的流れを改善
4. **SEO**: 重要キーワードを適切に配置
5. **Markdown**: 見出しと強調を活用

修正後の記事をMarkdown形式で返してください。
---
# [修正後のタイトル]

本文...
---
"""

    def _build_revision_prompt(
        self,
        title: str,
        content: str,
        feedback: str,
        concept: str,
    ) -> str:
        """修正用ユーザープロンプト"""
        prompt = f"""**現在の記事**:
# {title}

{content}

---

**修正フィードバック**: {feedback}
"""
        if concept:
            prompt += f"\n**記事コンセプト**: {concept}"

        prompt += "\n\nフィードバックを参考に、上記記事を修正してください。"
        return prompt

    # ======== レスポンス解析 ========

    def _parse_article_response(self, response: str) -> Dict[str, Any]:
        """生成された記事をパース"""
        # Markdown から タイトルと本文を抽出
        lines = response.split("\n")
        title = ""
        content_lines = []

        in_title = False
        for line in lines:
            if line.startswith("# ") and not title:
                title = line.replace("# ", "").strip()
                in_title = True
            elif in_title:
                content_lines.append(line)

        content = "\n".join(content_lines).strip()

        return {
            "title": title or "無題",
            "content": content or response,
            "thumbnail_prompt": f"{title} のイメージ画像",
        }

    def _parse_revision_response(self, response: str) -> Dict[str, Any]:
        """修正結果をパース"""
        lines = response.split("\n")
        title = ""
        content_lines = []

        in_title = False
        for line in lines:
            if line.startswith("# ") and not title:
                title = line.replace("# ", "").strip()
                in_title = True
            elif in_title:
                content_lines.append(line)

        content = "\n".join(content_lines).strip()

        return {
            "title": title,
            "content": content,
        }

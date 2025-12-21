import logging
import re
from typing import Dict, Any, List, Optional
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class ArticleContentGeneratorTask(BaseTaskModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = GeminiService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        article_concept = inputs.get("article_concept", {})
        texts = inputs.get("texts", [])
        source_content = "\n\n".join([str(t) for t in texts]) if isinstance(texts, list) else str(texts)
        blog = inputs.get("blog", {})
        title, content = self._generate_article_content(article_concept, source_content, blog)
        thumbnail_prompt = self._generate_thumbnail_prompt(title, content, article_concept)
        return {"title": title, "content": content, "thumbnail_prompt": thumbnail_prompt}

    def _generate_article_content(self, article_concept: Dict[str, Any], source_content: str, blog: Dict[str, Any]) -> tuple[str, str]:
        if not blog: raise ValueError("Blog config missing.")
        blog_name = blog.get("name", "")
        blog_description = blog.get("description", "")
        axes = article_concept.get("axes", [])
        axes_text = "\n".join([f"- {a.get('name')}: {a.get('description')} ({a.get('content_angle')})" for a in axes])
        prompt = (
            f"あなたは『{blog_name}』のライターです。高品質な記事を作成してください。\n"
            f"ブログ説明: {blog_description}\n"
            f"コンセプト: {article_concept}\n"
            f"記事の軸:\n{axes_text}\n"
            f"入力テキスト: {source_content[:2000]}\n"
            "ルール:\n"
            "1. 先頭に必ず「タイトル: [タイトル]」を記載する。\n"
            "2. セクションは [h2], [h3], [b], [li] のようなBBCode風タグで構成すること。\n"
            "3. プロンプトの説明や生成過程などのメタな記述は含めないこと。"
        )
        response = self.llm_service.generate_text(prompt, max_tokens=2000)
        title, content = self._parse_response(response)
        return title, self._convert_markers_to_markdown(content)

    def _convert_markers_to_markdown(self, text: str) -> str:
        text = re.sub(r'\[h2\]\s*(.*?)\s*\[/h2\]', r'## \1', text, flags=re.I | re.S)
        text = re.sub(r'\[h3\]\s*(.*?)\s*\[/h3\]', r'### \1', text, flags=re.I | re.S)
        text = re.sub(r'\[b\]\s*(.*?)\s*\[/b\]', r'**\1**', text, flags=re.I | re.S)
        text = re.sub(r'\[li\]\s*(.*?)\s*\[/li\]', r'- \1', text, flags=re.I | re.S)
        text = re.sub(r'\[li\]\s*', r'- ', text, flags=re.I)
        text = re.sub(r'\[h2\]\s*', r'## ', text, flags=re.I)
        text = re.sub(r'\[h3\]\s*', r'### ', text, flags=re.I)
        return text.strip()

    def _parse_response(self, response: str) -> tuple[str, str]:
        lines = response.strip().split('\n')
        title, content, in_content = "", "", False
        for line in lines:
            if line.startswith('タイトル:'): title = line.replace('タイトル:', '').strip()
            elif line.startswith('本文:'): in_content = True
            elif in_content: content += line + '\n'
            elif title and not in_content and line.strip():
                 in_content = True
                 content += line + '\n'
        if not title:
            title = lines[0].strip() if lines else "Untitled"
            content = "\n".join(lines[1:]) if len(lines) > 1 else ""
        return title.strip(), content.strip()

    def _generate_thumbnail_prompt(self, title: str, content: str, article_concept: Dict) -> str:
        clean = re.sub(r'[#*\->`\[\]()]', '', content[:1500])
        prompt = (
            f"タイトル『{title}』の4コマ漫画用サムネイル生成プロンプトを作成してください。\n"
            f"内容: {clean[:500]}\n"
            "フォーマット:\n1) 導入\n2) 展開\n3) どんでん返し\n4) 結末"
        )
        thumbnail_prompt = self.llm_service.generate_text(prompt, max_tokens=400)
        
        # Adopting proactively generated image (Scavenger support)
        if thumbnail_prompt and thumbnail_prompt.startswith("__IMAGE_URL__"):
            logger.info("Adopting proactively generated image URL.")
            return thumbnail_prompt

        return ' '.join(thumbnail_prompt.split())[:600] if thumbnail_prompt else "漫画風"

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "ArticleContentGenerator", "description": "Generates article content."}

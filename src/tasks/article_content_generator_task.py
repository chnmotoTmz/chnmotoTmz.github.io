import logging
import re
from typing import Dict, Any, List, Optional
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService
import os

logger = logging.getLogger(__name__)

class ArticleContentGeneratorTask(BaseTaskModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = GeminiService()

    def _generate_article_content(self, article_concept: Dict[str, Any], source_content: str, blog: Dict[str, Any]) -> tuple[str, str]:
        if not blog:
            raise ValueError(f"Blog config missing. Received: {blog} (type: {type(blog).__name__})")
        blog_name = blog.get("name", "")
        blog_description = blog.get("description", "")
        axes = article_concept.get("axes", [])
        axes_text = "\n".join([f"- {a.get('name')}: {a.get('description')} ({a.get('content_angle')})" for a in axes])
        
        # Load blog-specific prompt instructions
        custom_instructions = ""
        prompt_file = blog.get("prompt_file")
        if prompt_file:
            prompt_path = os.path.join("config", "prompts", prompt_file)
            if os.path.exists(prompt_path):
                try:
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        custom_instructions = f"\n\n【このブログ固有の執筆指示】\n{f.read()}\n"
                        logger.info(f"Loaded custom instructions from {prompt_file}")
                except Exception as e:
                    logger.warning(f"Failed to load prompt file {prompt_file}: {e}")

        prompt = (
            f"あなたは『{blog_name}』のライターとして、読者の心に響く人間味あふれるブログ記事を執筆してください。\n\n"
            f"【ブログ情報】\n名前: {blog_name}\n説明: {blog_description}\n"
            f"{custom_instructions}\n"
            f"【コンセプト】\n{article_concept}\n\n"
            f"【独自の切り口】\n{axes_text}\n\n"
            f"【参考情報】\n{source_content[:2500]}\n\n"
            "【執筆・構成の鉄則】\n"
            "1. 見出し（<h2>, <h3>）は、週刊誌の煽り見出しのように「短く・鋭く・キャッチー」にしてください。絶対に15文字を超えてはいけません。見出しタグの中に本文を書くのは厳禁です。\n"
            "2. 本文（段落）は必ず <p> タグで囲むか、タグなしのプレーンテキストとして記述してください。見出しタグの直後に本文を繋げないでください。\n"
            "3. 重要な箇所は <b> タグで強調してください。\n"
            "4. 箇条書きは <li> タグを使用してください。\n"
            "5. 先頭に必ず「タイトル: [タイトル]」を記載すること。\n"
            "6. 生成過程の解説、挨拶、CSSブロック、および『次に私ができること』といったメタな記述は**死んでも含めない**でください。\n\n"
            "【★最重要：ライターの『魂』を込める】\n"
            "これは自動生成記事ではなく、あなたの個人的なブログです。以下の「人間らしい痕跡」を過剰なほどに織り交ぜてください：\n"
            "- 文中に「え、これマジで？」「正直、私は引きました…」「これ、最高じゃないですか？」といった個人的な驚き、本音、ボヤキを自然に挿入してください。\n"
            "- 読者に「実はここだけの話ですが…」「皆さんはどう思いますか？」と親しみやすく語りかけてください。\n"
            "- 文末や感情が動くポイントで、効果的に絵文字（✨, 🚀, 😅, 😱, 💪, ㊙️など）を使用してください。\n"
            "- 教科書的な解説を徹底的に排除し、ライターの体温と個性が伝わる「生きた文章」に仕上げてください。\n"
        )
        response = self.llm_service.generate_text(prompt, max_tokens=2500)
        title, content = self._parse_response(response)
        
        # Ensure [:contents] exists if the LLM forgot it
        if "[:contents]" not in content:
            content = "[:contents]\n\n" + content
            
        return title, content

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ArticleContentGeneratorTask] Received inputs: {list(inputs.keys())}")
        blog = inputs.get("blog")
        logger.info(f"[ArticleContentGeneratorTask] Blog input type: {type(blog).__name__}")
        
        article_concept = inputs.get("article_concept", {})
        texts = inputs.get("texts", [])
        source_content = "\n\n".join([str(t) for t in texts]) if isinstance(texts, list) else str(texts)
        blog = inputs.get("blog", {})
        images = inputs.get("images_for_prompt", [])

        title, content = self._generate_article_content(article_concept, source_content, blog)
        
        # --- Physical Image Injection (User Uploaded Photos) ---
        if images:
            logger.info(f"Injecting {len(images)} user-uploaded images into content.")
            image_md = ""
            for img in images:
                url = img.get("url")
                desc = img.get("description") or "ユーザー提供写真"
                if url:
                    image_md += f"\n\n<div class='user-photo'>\n<img src='{url}' alt='{desc}' width='100%'/>\n<p><small>{desc}</p>\n</div>\n\n"
            
            # Prepend user images after the TOC tag if present
            if "[:contents]" in content:
                parts = content.split("[:contents]", 1)
                content = parts[0] + "[:contents]\n" + image_md + parts[1]
            else:
                content = image_md + content

        thumbnail_prompt = self._generate_thumbnail_prompt(title, content, article_concept)
        
        # Return content with HTML tags - conversion happens at posting stage
        return {"title": title, "content": content, "thumbnail_prompt": thumbnail_prompt}

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

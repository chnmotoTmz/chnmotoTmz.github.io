"ArticleContentGeneratorTask - 記事コンテンツ生成タスク"
import logging
import re
from typing import Dict, Any, List, Optional

from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class ArticleContentGeneratorTask(BaseTaskModule):
    """
    記事のコンセプトと入力コンテンツに基づいて、記事本文とサムネイルプロンプトを生成するタスク。
    LLM動的判断版：ルールベースを排除し、AIがコンテンツから最適なスタイルを決定。
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_service = GeminiService()

    @staticmethod
    def get_module_info() -> Dict[str, Any]:
        """Returns module information for registration."""
        return {
            "name": "ArticleContentGenerator",
            "description": "Generates article content and thumbnail prompt based on concept.",
            "inputs": {
                "article_concept": "Dict",
                "texts": "List[str] (optional)",
                "blog": "Dict (optional)"
            },
            "outputs": {
                "title": "str",
                "content": "str",
                "thumbnail_prompt": "str"
            }
        }

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the article generation task.
        """
        logger.info("Starting ArticleContentGeneratorTask...")
        
        article_concept = inputs.get("article_concept", {})
        
        # Source content extraction
        texts = inputs.get("texts", [])
        source_content = ""
        if isinstance(texts, list):
            source_content = "\n\n".join([str(t) for t in texts])
        elif isinstance(texts, str):
            source_content = texts
            
        blog = inputs.get("blog", {})
        new_chat = inputs.get("new_chat", False)
        
        # 1. Generate Article Content
        title, content = self._generate_article_content(article_concept, source_content, blog, new_chat)
        
        # 2. Generate Thumbnail Prompt
        thumbnail_prompt = self._generate_thumbnail_prompt(title, content, article_concept, new_chat)
        
        logger.info("Article generated: %s", title)
        
        return {
            "title": title,
            "content": content,
            "thumbnail_prompt": thumbnail_prompt
        }

    def _generate_article_content(self, article_concept: Dict[str, Any], source_content: str, blog: Dict[str, Any], new_chat: bool) -> tuple[str, str]:
        """
        コンセプトとソースコンテンツから記事を生成する
        """
        theme = article_concept.get("theme", "")
        genre = article_concept.get("genre", "")
        keywords = article_concept.get("keywords", [])
        target_audience = article_concept.get("target_audience", "")
        writing_tone = article_concept.get("writing_tone", "")
        axes = article_concept.get("axes", [])
        
        blog_name = blog.get("name", "")
        blog_description = blog.get("description", "")
        
        axes_text = ""
        for axis in axes:
            axes_text += f"- {axis.get('name')}: {axis.get('description')} ({axis.get('content_angle')})\n"
            
        prompt = f"""あなたはブログ「{blog_name}」のライターです。
以下のコンセプトと情報に基づいて、読者を引き込む魅力的なブログ記事を作成してください。

【ブログ情報】
名前: {blog_name}
概要: {blog_description}

【記事コンセプト】
テーマ: {theme}
ジャンル: {genre}
ターゲット読者: {target_audience}
文体（トーン）: {writing_tone}
キーワード: {', '.join(keywords)}

【独自の切り口（軸）】
{axes_text}

【元ネタ・参考情報】
{source_content[:2000]}

【重要：出力ルール】
- 「承知いたしました」「記事を作成します」などの挨拶や前置きは**一切禁止**です。
- 出力は必ず「タイトル」から始めてください。
- 余計な説明文を含めず、記事の本文のみを出力してください。

【要件】
- はてなブログのMarkdown記法を使用してください。
- 読者が共感し、役に立つと感じる内容にしてください。
- 構成は「導入」「本文（見出し付き）」「まとめ」の流れにしてください。
- 具体的で魅力的なタイトルをつけてください。
- URLは一切記述しないでください。
- 絵文字は適度に使用してください。

【出力形式】
タイトル: [タイトル]

本文:
[Markdown本文]
"""
        try:
            response = self.llm_service.generate_text(
                prompt,
                model_name=None, # Use default
                max_tokens=2000,
                mode='writing',
                new_chat=new_chat
            )
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Failed to generate article content: {e}")
            raise

    def _parse_response(self, response: str) -> tuple[str, str]:
        """
        LLMレスポンスを解析してタイトルと本文を抽出
        """
        lines = response.strip().split('\n')
        title = ""
        content = ""
        
        in_content = False
        for line in lines:
            if line.startswith('タイトル:'):
                title = line.replace('タイトル:', '').strip()
            elif line.startswith('本文:'):
                in_content = True
            elif in_content:
                content += line + '\n'
            # Fallback if "本文:" is missing but title is found
            elif title and not in_content and line.strip() and not line.startswith('タイトル:'):
                 in_content = True
                 content += line + '\n'
        
        if not title:
            # タイトルが見つからない場合、最初の行をタイトルとする
            title = lines[0].strip() if lines else "無題"
            content = "\n".join(lines[1:]) if len(lines) > 1 else ""
        
        return title.strip(), content.strip()

    def _determine_manga_style(self, genre: str, theme: str, title: str, content_preview: str = "") -> str:
        """
        LLMを使ってコンテンツに最適な漫画スタイルを動的に決定する。
        """
        
        # LLMに判断させるプロンプト
        style_prompt = f"""以下の記事に最適な漫画スタイルを決定してください。

【記事情報】
タイトル: {title}
ジャンル: {genre}
テーマ: {theme}
内容: {content_preview[:300]}

【要件】
- 実在の作品名や作家名は使わない
- 画像生成AIが理解できる具体的な視覚表現で説明
- 記事の雰囲気に最も合うスタイルを選択

【出力形式】
「○○風」という形式で、括弧内に具体的な視覚要素を箇条書き。

例：
熱血バトル漫画風（ダイナミックな構図、スピード感のある線、迫力ある効果線、躍動感あふれるキャラクター）

出力は1行のみ。前置き不要。"""

        try:
            response = self.llm_service.generate_text(
                style_prompt,
                model_name=None,
                max_tokens=200,
                mode='fast'
            )
            
            if response and len(response.strip()) > 10:
                style = response.strip()
                # 余計な前置きを削除
                style = self._clean_llm_response(style)
                logger.info(f"🎨 LLMが選択したスタイル: {style[:100]}...")
                return style
            else:
                logger.warning("LLM returned empty style. Using fallback.")
                return self._get_default_manga_style()
                
        except Exception as e:
            logger.error(f"❌ Failed to determine manga style with LLM: {e}")
            return self._get_default_manga_style()


    def _get_default_manga_style(self) -> str:
        """
        LLM失敗時のデフォルトスタイル
        """
        return "親しみやすい日常漫画風（読みやすいキャラクター、コミカルな表情、バランスの良い構成、万人受けするタッチ）"


    def _generate_thumbnail_prompt(self, title: str, content: str, article_concept: Dict, new_chat: bool = False) -> str:
        """
        記事から四コマ漫画風のサムネイル画像プロンプトをLLMで生成。
        スタイルもLLMが動的に決定。
        """
        
        # 本文から概要を抽出
        clean_content = re.sub(r'[#*\->`\[\]()]', '', content[:1500])
        clean_content = ' '.join(clean_content.split())
        
        concept_theme = article_concept.get('theme', 'ブログ記事')
        concept_genre = article_concept.get('genre', '一般')
        
        # LLMに漫画スタイルを決定させる
        manga_style = self._determine_manga_style(
            concept_genre, 
            concept_theme, 
            title,
            clean_content[:300]
        )
        
        # 四コマ漫画プロンプト生成
        llm_prompt = f"""記事の内容を四コマ漫画で表現してください。

【記事】{title}
{clean_content[:500]}

【スタイル】{manga_style}

【出力形式】以下の形式のみ出力（前置き不要）:
１）起：場面と「セリフ」
２）承：展開と「セリフ」
３）転：意外な展開と「セリフ」
４）結：オチと「セリフ」

各コマは簡潔に（1-2文）。セリフは「」で囲む。

例：
１）起：山道を歩く二人「紅葉きれい！」
２）承：不思議な種を発見「これ何？」
３）転：地元民が登場「それはお守りの種だよ」
４）結：感動する二人「体験って面白い！」"""
        
        try:
            thumbnail_prompt = self.llm_service.generate_text(
                llm_prompt,
                model_name=None,
                max_tokens=400,
                mode='fast',
                new_chat=new_chat
            )
            
            if thumbnail_prompt:
                # 前置きを削除
                thumbnail_prompt = self._clean_llm_response(thumbnail_prompt)
                # 改行・空行を除去して1行化
                thumbnail_prompt = ' '.join(thumbnail_prompt.split())
                # 600文字制限
                if len(thumbnail_prompt) > 600:
                    thumbnail_prompt = thumbnail_prompt[:600]
                # スタイル指定を末尾に追加
                thumbnail_prompt = f"{thumbnail_prompt.strip()} 【スタイル】{manga_style}"
                logger.info(f"🖼️ Generated manga thumbnail prompt: {thumbnail_prompt[:150]}...")
                return thumbnail_prompt
            else:
                logger.warning("LLM returned empty thumbnail prompt. Using fallback.")
                return self._fallback_thumbnail_prompt(title, clean_content, manga_style)
                    
        except Exception as e:
            logger.error(f"❌ Failed to generate thumbnail prompt with LLM: {e}")
            return self._fallback_thumbnail_prompt(title, clean_content, manga_style)


    def _fallback_thumbnail_prompt(self, title: str, content_summary: str, manga_style: str = None) -> str:
        """
        LLM 生成が失敗した場合のフォールバック用プロンプト。
        """
        if not manga_style:
            manga_style = self._get_default_manga_style()
        
        return f"""「{title}」をテーマにした四コマ漫画。

起承転結の流れで、最後にオチがある。セリフと吹き出し付き。
記事の内容: {content_summary[:200]}

【スタイル】{manga_style}"""


    def _clean_llm_response(self, response: str) -> str:
        """LLMレスポンスから前置きや余計な文言を削除"""
        
        # 前置きパターンを削除
        prefixes_to_remove = [
            r'^承知いたしました[。、]?\s*',
            r'^了解しました[。、]?\s*',
            r'^はい[、。]?\s*',
            r'^わかりました[。、]?\s*',
            r'^かしこまりました[。、]?\s*',
            r'^以下のように.*?[:：]\s*',
            r'^それでは.*?[:：]\s*',
        ]
        
        cleaned = response.strip()
        for pattern in prefixes_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
        return cleaned.strip()
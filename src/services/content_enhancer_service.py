"""
Unified content enhancer built on top of multiple LLM providers.

This module replaces the legacy ``src.services.article.content_enhancer_claude4``
location so that the enhancer lives alongside other service-level integrations.
"""

from __future__ import annotations

import logging
import re
import os
import time
from typing import List, Dict, Tuple, Optional

from src.services.gemini_service import GeminiService
from src.services.claude_service import ClaudeService

logger = logging.getLogger(__name__)


class ContentEnhancerLLM:
    """Generate article drafts by delegating to a configured LLM provider."""

    def __init__(self, model: Optional[str] = None, llm_service: Optional[GeminiService] = None, blog_id: Optional[str] = None):
        """Initialise enhancer with a default LLM model and optional blog-specific prompt."""
        try:
            # Choose LLM provider: allow switching to Claude via env var
            provider = os.getenv('ARTICLE_LLM_PROVIDER', '').lower()
            if llm_service:
                self.llm_service = llm_service
            elif provider == 'claude':
                # create Claude client
                api_key = os.getenv('CLAUDE_API_KEY')
                model_name = model or os.getenv('CLAUDE_MODEL')
                self.llm_service = ClaudeService(api_key=api_key, model=model_name)
            else:
                # Initialize GeminiService by default
                self.llm_service = llm_service or GeminiService()
            self.model = model  # If None, GeminiService will select the best available model
            self.blog_id = blog_id
            self.custom_prompt = self._load_blog_prompt(blog_id) if blog_id else None
            
            # Load and append common markdown rules
            common_rules = self._load_common_rules()
            if common_rules:
                if self.custom_prompt:
                    self.custom_prompt += "\n" + common_rules
                else:
                    self.custom_prompt = common_rules
                    
            logger.info("ContentEnhancerLLMはモデル '%s' を使用して初期化されました。", self.model)
            if self.custom_prompt:
                logger.info("ブログID '%s' のカスタムプロンプト（共通ルール含む）をロードしました。", blog_id)
        except Exception as e:
            logger.error("ContentEnhancerLLMの初期化に失敗しました: %s", e)
            raise

    def _load_blog_prompt(self, blog_id: str) -> Optional[str]:
        """Load blog-specific prompt from data directory."""
        if not blog_id:
            logger.info("blog_id が指定されていないため、ブログプロンプトをスキップします")
            return None
        
        # Extract base blog_id (without domain) if it contains a domain
        base_blog_id = blog_id.split('.')[0] if '.' in blog_id else blog_id
        logger.debug(f"ブログプロンプト検索: オリジナル blog_id='{blog_id}', ベース blog_id='{base_blog_id}'")
        
        # Try exact match first
        prompt_file = os.path.join("data", f"blog_main_prompt_{blog_id}.txt")
        if os.path.exists(prompt_file):
            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    logger.info(f"ブログプロンプトファイル '{prompt_file}' を読み込みました")
                    return content
            except Exception as e:
                logger.warning(f"ブログプロンプトファイル '{prompt_file}' の読み込みに失敗しました: {e}")

        # Try with base blog_id
        if base_blog_id != blog_id:
            prompt_file = os.path.join("data", f"blog_main_prompt_{base_blog_id}.txt")
            if os.path.exists(prompt_file):
                try:
                    with open(prompt_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        logger.info(f"ブログプロンプトファイル '{prompt_file}' を読み込みました (ベース blog_id を使用)")
                        return content
                except Exception as e:
                    logger.warning(f"ブログプロンプトファイル '{prompt_file}' の読み込みに失敗しました: {e}")

        # Try case-insensitive match for files starting with blog_main_prompt_
        data_dir = "data"
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                if filename.startswith("blog_main_prompt_") and filename.endswith(".txt"):
                    # Extract blog identifier from filename (remove prefix and suffix)
                    file_blog_id = filename[len("blog_main_prompt_"):-len(".txt")]
                    # Case-insensitive comparison with both original and base blog_id
                    if (file_blog_id.lower() == blog_id.lower() or 
                        file_blog_id.lower() == base_blog_id.lower()):
                        prompt_file = os.path.join(data_dir, filename)
                        try:
                            with open(prompt_file, "r", encoding="utf-8") as f:
                                content = f.read().strip()
                                logger.info(f"ブログプロンプトファイル '{prompt_file}' を読み込みました (大文字小文字を無視してマッチ)")
                                return content
                        except Exception as e:
                            logger.warning(f"ブログプロンプトファイル '{prompt_file}' の読み込みに失敗しました: {e}")

        logger.info(f"ブログID '{blog_id}' (ベース: '{base_blog_id}') のプロンプトファイルが見つかりませんでした")
        return None

    def _load_common_rules(self) -> Optional[str]:
        """Load common markdown rules from data directory."""
        common_file = os.path.join("data", "common_markdown_rules.txt")
        if os.path.exists(common_file):
            try:
                with open(common_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    logger.info(f"共通Markdownルール '{common_file}' を読み込みました")
                    return content
            except Exception as e:
                logger.warning(f"共通Markdownルール '{common_file}' の読み込みに失敗しました: {e}")
        return None

    def enhance_and_generate(self, texts: List[str], images: List[Dict], max_retries: int = 5, rag_context: str = "", structure: List[Dict] = None, affiliate_strategy: Dict = None, style_prompt: str = "", content_analysis: Dict = None, article_concept: Dict = None) -> Tuple[str, str]:
        """Generate a Markdown article draft from the provided context."""
        if not texts and not images:
            raise ValueError("生成するコンテンツがありません。")

        logger.info(f"{len(texts)}件のテキストと{len(images)}件の画像からコンテンツを生成します。")
        if style_prompt:
            logger.info(f"スタイル指示: {style_prompt}")

        combined_content = self._prepare_content(texts, images)

        for attempt in range(max_retries):
            try:
                result = self._generate_with_llm(combined_content, rag_context, structure, affiliate_strategy, style_prompt, content_analysis, article_concept)
                if result and result[0] and result[1]:
                    logger.info(f"試行 {attempt + 1} 回目でコンテンツ生成に成功しました。")
                    return result[0].strip(), result[1].strip()

                logger.warning(f"試行 {attempt + 1} 回目で空の結果が返されました。")

            except Exception as e:
                logger.warning(f"試行 {attempt + 1} 回目でエラーが発生しました: {e}", exc_info=True)
                if attempt == max_retries - 1:
                    logger.error("最大リトライ回数に達したため、コンテンツ生成を中止します。")
                    # エラーメッセージを返すのではなく、例外を発生させてワークフローを停止させる
                    raise RuntimeError(f"記事生成に失敗しました (全リトライ失敗): {e}") from e

            # Outer attempt backoff to avoid tight retry loops that may skip in-flight wrapper replies
            if attempt < max_retries - 1:
                outer_wait = 2 + attempt * 2
                logger.info(f"Outer retry {attempt+2} will start after {outer_wait}s backoff")
                try:
                    time.sleep(outer_wait)
                except Exception:
                    pass

        # ここに到達することはないはずだが、念のため
        raise RuntimeError("記事生成に失敗しました (不明なエラー)")

    def _prepare_content(self, texts: List[str], images: List[Dict]) -> str:
        """AIプロンプト用に、テキストと画像情報を結合したコンテンツ文字列を準備します。

        NOTE: この実装では、テキストと画像を別々にグループ化していますが、
        時系列的な文脈を保持するためには、呼び出し元で時系列順に並べ替えた
        統合リストを渡す必要があります。
        """
        parts = []

        if texts and images:
            parts.append("【投稿内容（時系列順）】")
            parts.append("※以下のテキストと画像は、ユーザーが投稿した順序で並んでいます。")
            parts.append("※文脈を考慮して、適切な位置に画像を配置してください。\n")

        if texts:
            if not images:
                parts.append("【テキスト内容】")
            for i, text in enumerate(texts, 1):
                if text.strip():
                    parts.append(f"テキスト{i}: {text.strip()}")

        if images:
            if not texts:
                parts.append("【画像情報】")
            for i, img in enumerate(images, 1):
                desc = img.get('description', '').strip()
                url = img.get('url', '').strip()
                if desc or url:
                    parts.append(f"\n画像{i}: {desc or '画像'}")
                    parts.append(f"URL: {url}")
                    parts.append("※ この画像を記事内で使用する際は、Markdown形式 ![altテキスト](URL) で埋め込んでください。")

        return "\n".join(parts)

    def _save_prompt_to_log(self, prompt: str) -> None:
        """Save the full prompt to a dedicated prompts log file."""
        try:
            import os
            from pathlib import Path
            from datetime import datetime
            
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            # Create prompts log file with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_filename = logs_dir / f"prompts_{timestamp}.log"
            
            # If there's a current Gemini session log configured, append the prompt there
            try:
                from src.utils.gemini_logger import get_log_file, log_gemini_interaction
                session_file = get_log_file()
            except Exception:
                session_file = None

            if session_file:
                try:
                    # Use the unified gemini logging format so the viewer can show prompt + interactions in one file
                    log_gemini_interaction(module_name="ContentEnhancerLLM", prompt=prompt, response=None, model="prompt")
                    return
                except Exception:
                    # Fall back to separate prompts file on any error
                    pass

            with open(log_filename, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | DEBUG    | src.services.content_enhancer_service | 📝 Content Generation Prompt:\n")
                f.write(prompt)
                f.write("\n" + "="*100 + "\n")
                
        except Exception as e:
            logger.warning(f"Failed to save prompt to log: {e}")

    def _determine_article_type(self, content_analysis: Dict, structure: List[Dict]) -> str:
        """投稿内容から記事タイプを判定"""
        if not content_analysis:
            return "standard"
        
        info_level = content_analysis.get('info_level', 'moderate')
        has_products = content_analysis.get('has_product_mentions', False)
        
        if info_level == "detailed" and has_products:
            return "detailed_review"
        elif has_products or (structure and len(structure) >= 5):
            return "experience_with_gear"
        elif info_level == "minimal":
            return "simple_story"
        else:
            return "standard"

    def _build_dynamic_prompt(self, article_type: str, content_analysis: Dict, 
                             structure: List[Dict], affiliate_strategy: Dict, style_prompt: str) -> str:
        """記事タイプに応じた動的プロンプトを生成"""
        
        # 基本情報
        char_count = content_analysis.get('char_count', 0) if content_analysis else 0
        
        # ブログ設定の文字数制限を優先
        max_article_length = content_analysis.get('max_article_length') if content_analysis else None
        if max_article_length:
            target_chars = max_article_length
            logger.info(f"ブログ設定の文字数制限を適用: {max_article_length}文字")
        else:
            target_chars = char_count * 3 if char_count < 200 else char_count * 2
        
        prompt_parts = []
        
        # 記事タイプ別の指示
        if article_type == "detailed_review":
            prompt_parts.append(f"""
【記事タイプ】: 詳細ギアレビュー

【指定構成】:
{self._format_structure(structure)}

【アフィリエイト戦略】:
{self._format_affiliate_strategy(affiliate_strategy)}
- 各セクションで積極的に商品紹介
- 投稿で言及された商品を優先
""")
        
        elif article_type == "experience_with_gear":
            prompt_parts.append(f"""
【記事タイプ】: 体験談＋ギア紹介

【制約】:
- 目標文字数: {target_chars}文字
- 体験談をメインに、使用ギアは1セクションにまとめる
- 投稿で言及された商品のみ紹介

【指定構成】:
{self._format_structure(structure)}
""")
        
        elif article_type == "simple_story":
            prompt_parts.append(f"""
【記事タイプ】: シンプルな体験談

【制約】:
- 投稿内容: {char_count}文字（情報少）
- 目標文字数: {target_chars}文字以内
- セクション数: 3-4個
- 商品紹介: 最小限または無し
- **重要**: 投稿に無い情報で500文字以上書かない

【指定構成】:
{self._format_structure(structure)}
""")
        
        else:  # standard
            prompt_parts.append(f"""
【記事タイプ】: 標準

【制約】:
- 目標文字数: {target_chars}文字
- 投稿内容に応じた適切な構成

【指定構成】:
{self._format_structure(structure)}
""")
        
        # スタイル指示があれば追加
        if style_prompt:
            prompt_parts.append(f"\n【スタイル指示】:\n{style_prompt}")
        
        return "\n".join(prompt_parts)

    def _format_structure(self, structure: List[Dict]) -> str:
        """構成をフォーマット"""
        if not structure:
            return "（構成指定なし）"
        
        formatted = []
        for i, section in enumerate(structure, 1):
            title = section.get('section_title', f'セクション{i}')
            outline = section.get('content_outline', '')
            length = section.get('estimated_length', '')
            formatted.append(f"{i}. {title} ({length})\n   {outline}")
        
        return "\n".join(formatted)
    
    def _format_affiliate_strategy(self, strategy: Dict) -> str:
        """アフィリエイト戦略をフォーマット"""
        if not strategy:
            return "（戦略指定なし）"
        
        amazon = strategy.get('amazon_keywords', [])
        rakuten = strategy.get('rakuten_keywords', [])
        advice = strategy.get('placement_advice', '')
        
        return f"""
Amazon: {', '.join(amazon)}
楽天: {', '.join(rakuten)}
配置アドバイス: {advice}
"""

    def _generate_with_llm(self, content: str, rag_context: str = "", structure: List[Dict] = None, affiliate_strategy: Dict = None, style_prompt: str = "", content_analysis: Dict = None, article_concept: Dict = None) -> Optional[Tuple[str, str]]:
        """Call the configured LLM and parse the structured Markdown response."""
        
        # 投稿内容分析に基づく動的プロンプト
        dynamic_instruction = ""
        if content_analysis:
            article_type = self._determine_article_type(content_analysis, structure)
            dynamic_instruction = self._build_dynamic_prompt(article_type, content_analysis, structure, affiliate_strategy, style_prompt)
        
        # RAGコンテキストがある場合の追加指示
        rag_instruction = ""
        if rag_context:
            rag_instruction = f"""
【参考情報（過去記事・スタイル）】
以下の情報は、過去の類似記事や文体の参考資料です。
これらは「文体」や「背景知識」として活用してください。
重要：過去記事の内容をそのままコピーしたり、単に要約したりしないでください。
新しい記事は、これらの過去記事を踏まえた上で、「内容を深化・発展」させたり、「新しい視点」を加えたりして、
読者にとって新しい価値があるものにしてください（自己参照ループの回避）。

{rag_context}
"""

        # 記事構成案がある場合の追加指示
        structure_instruction = ""
        if structure:
            structure_lines = []
            for i, section in enumerate(structure, 1):
                structure_lines.append(f"{i}. {section.get('section_title', '見出し')}")
                structure_lines.append(f"   - 内容: {section.get('content_outline', '')}")
                structure_lines.append(f"   - 目安文字数: {section.get('estimated_length', '400文字')}")
            structure_instruction = f"""
【記事構成案（必ず従うこと）】
以下の構成に従って記事を執筆してください。見出しの順序と内容を厳守すること。

{chr(10).join(structure_lines)}
"""

        # アフィリエイト戦略がある場合の追加指示
        affiliate_instruction = ""
        if affiliate_strategy:
            affiliate_instruction = f"""
【アフィリエイト戦略（重要）】

記事内で以下の商品を自然な文脈で紹介してください。商品名やキーワードをテキストとして自然に記述し、URLやリンク記法を追加しないでください（後の工程で自動的にリンクが挿入されます）。

- Amazon検索キーワード: {', '.join(affiliate_strategy.get('amazon_keywords', []))}
- 楽天検索キーワード: {', '.join(affiliate_strategy.get('rakuten_keywords', []))}
- 配置アドバイス: {affiliate_strategy.get('placement_advice', '')}

注意: 
- 商品紹介は記事の流れに自然に溶け込むようにし、押し売り感を出さないこと。
- URLやリンク記法を追加せず、商品名を自然なテキストとして記述すること。
- 例: 「ノイズキャンセリングイヤホンを使ってみると快適です」のように記述。
- 「参考: URL」形式は使用しない。
"""

        # スタイル指示がある場合の追加指示
        style_instruction = ""
        if style_prompt:
            style_instruction = f"""
【文体・スタイル指示（最重要・最優先）】
以下のスタイル指示を厳守してください。これは他の指示よりも優先されます。
{style_prompt}

重要: このスタイル指示を無視せず、必ず反映してください。
例えば「300字ぐらいのブログ記事」と指定されたら、必ず約300文字程度の短い記事にしてください。
例えば「ギャル語で絵文字満載」と指示されたら、本当にギャル風の言葉遣いと絵文字を多用してください。
"""

        # Article concept axes - request supplemental content by axis
        axes_instruction = ""
        try:
            if article_concept and isinstance(article_concept, dict):
                axes = article_concept.get('axes') or []
                if isinstance(axes, list) and len(axes) > 0:
                    axes_lines = ["\n【記事を立体化する補助軸（axes）】\n考慮すべき軸ごとに、本文に短い補足段落（2〜4文）を追加してください。各補足は見出し(###) + 1段落で、元の記事の流れに自然に組み込まれるようにしてください。\n"]
                    for ax in axes[:3]:
                        name = ax.get('name', '').strip() or '軸'
                        desc = ax.get('description', '').strip() or ''
                        angle = ax.get('content_angle', '').strip() or ''
                        axes_lines.append(f"- {name}: {desc} → 補足案: {angle}")

                    axes_instruction = "\n" + "\n".join(axes_lines) + "\n"
        except Exception:
            axes_instruction = ""

        # 共通の必須ルール（目次タグなど）
        common_rules = """
【必須ルール】
- 記事の冒頭（リード文の後、最初の見出しの前）に、はてなブログの目次記法 `[:contents]` を必ず挿入すること（角括弧 [] を省略しないこと）。
- 本文全体はMarkdownで記述し、HTMLタグは使用しない。
- 画像がある場合は `![altテキスト](URL)` 形式で挿入する。
- **重要: コピー禁止** - 入力されたウェブ要約やテキストをそのままコピーせず、必ず独自の言葉で再構成してください。引用は最小限にし、必ず出典を明記してください。
"""

        # Use custom blog prompt if available, otherwise use default
        if self.custom_prompt:
            prompt = f"""{dynamic_instruction}

{self.custom_prompt}

{rag_instruction}
{structure_instruction}
{affiliate_instruction}
{common_rules}
{axes_instruction}

【今回の投稿内容（入力情報）】
{content}

出力フォーマットは厳密に次の通りにしてください：

タイトル: [読者の興味を引く、具体的で魅力的なタイトル（40文字以内）]

本文 (Markdown):
[Markdown構文を使用した本文。見出しは##、小見出しは###を使い、段落は空行で区切ること。]
"""
        else:
            prompt = f"""{dynamic_instruction}

以下の情報をもとに、はてなブログ向けの記事原案を作成してください。

{rag_instruction}
{structure_instruction}
{affiliate_instruction}
{common_rules}

{axes_instruction}

【今回の投稿内容】
{content}

出力フォーマットは厳密に次の通りにしてください：

タイトル: [読者の興味を引く、具体的で魅力的なタイトル（40文字以内）]

本文 (Markdown):
[Markdown構文を使用した本文。見出しは##、小見出しは###を使い、段落は空行で区切ること。]

追加ルール：
- 本文全体はMarkdownで記述し、HTMLタグは使用しない。
- 画像がある場合は `![altテキスト](URL)` 形式で挿入する。
- 箇条書きは `- ` または `1.` を使用する。
- 日本語で自然かつ信頼感のある文体にする。
- 過去記事（参考情報）がある場合は、それと重複しないように新しい情報を盛り込むこと。
- 記事の冒頭（リード文の後、最初の見出しの前）に、はてなブログの目次記法 `[:contents]` を必ず挿入すること（角括弧 [] を省略しないこと）。
- **重要: コピー禁止** - 入力されたウェブ要約やテキストをそのままコピーせず、必ず独自の言葉で再構成してください。引用は最小限にし、必ず出典を明記してください。
"""

        try:
            # enforce explicit instruction to avoid returning status/heartbeat replies
            prompt += "\n\n重要: このリクエストに対してはステータスやヘルスチェックの短い返信（例: 'Pong', 'I'm here', 'heartbeat'）を絶対に出力しないでください。\n出力は必ず記事のタイトルと本文のみを返してください。\n"

            # ★ プロンプト本体をログに出力（デバッグ用）
            prompt_preview = prompt[:800] if len(prompt) > 800 else prompt
            logger.debug(f"【LLM プロンプト本体】\n{prompt_preview}")
            if len(prompt) > 800:
                logger.debug(f"【プロンプト省略】残り {len(prompt) - 800} 文字...")
            
            # ★ プロンプトを専用ログファイルに保存
            self._save_prompt_to_log(prompt)
            
            # 記事生成は重要タスクなので高性能モデルを使用
            # 少しウェイトを入れて、外部ラッパーやブラウザ拡張が内部処理を完了する時間を確保する
            try:
                time.sleep(0.6)
            except Exception:
                pass
            response = self.llm_service.generate_text(
                prompt,
                model_name=self.model,
                max_tokens=3500,
                temperature=0.4,
                task_priority="high",  # 高性能モデル（gemini-2.5-pro等）を優先
            )
            # Detect ping/heartbeat-like responses (e.g., "Pong! I'm here...") and retry a few times
            def _is_ping_like(text: str) -> bool:
                if not text:
                    return True
                s = text.strip()
                # explicit indicators of heartbeat/status
                if re.search(r"\bpong\b|\bping\b|\bI am here\b|\bI'm here\b|\blistening\b|\bheartbeat\b|\bready\b", s, re.IGNORECASE):
                    return True
                # very short replies are suspicious
                if len(s) < 200 and not re.search(r"タイトル|本文|^#|##|本文 \(|本文\s*:\s|\b記事\b", s, re.IGNORECASE):
                    return True
                # if reply is mostly a single short sentence without markdown/article markers
                sentences = re.split(r"[\.。！？!?]", s)
                if len(s) < 300 and len(sentences) <= 2 and not re.search(r"##|###|タイトル|本文", s, re.IGNORECASE):
                    return True
                return False

            if not response:
                return None

            if _is_ping_like(response):
                logger.warning("LLM returned a ping-like or too-short response; performing internal retries before parsing.")
                # Save the ping response to prompts log for debugging
                try:
                    self._save_prompt_to_log(f"PING_RESPONSE:\n{response}")
                except Exception:
                    pass
                # small internal retry loop (stronger/backoff and more attempts)
                for ir in range(5):
                    try:
                        wait = 1 + ir * 3
                        logger.info(f"Internal retry {ir+1} after {wait}s")
                        time.sleep(wait)
                        response = self.llm_service.generate_text(
                            prompt,
                            model_name=self.model,
                            max_tokens=3500,
                            temperature=0.4,
                            task_priority="high",
                        )
                        if response and not _is_ping_like(response):
                            logger.info("Internal retry succeeded with non-ping response.")
                            break
                    except Exception as e:
                        logger.warning(f"Internal retry {ir+1} failed: {e}")

            if not response:
                return None
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error("LLM APIとの通信中にエラーが発生しました: %s", e, exc_info=True)
            raise

        # 安全措置: outer loopの各試行間に短めのバックオフ待機を入れる（呼び出し元の enhance_and_generate で制御）

    def _parse_llm_response(self, response: str) -> Optional[Tuple[str, str]]:
        """Parse the response string and extract title/Markdown content.

        Robust to variants:
        - With labels: 「タイトル: …」「本文 (Markdown):」
        - Without labels: leading Markdown heading (e.g. "# " or "## ") as title
        - Fallbacks: first non-empty line as title and the rest as content
        """
        logger.info("LLMレスポンス全文: %s", response)

        # 0) Normalize by removing code fences
        cleaned = re.sub(r"```(?:json|markdown)?\s*|\s*```", "", response).strip()

        title: Optional[str] = None
        content: Optional[str] = None

        # 1) Try labeled title
        m_title = re.search(r"^\s*タイトル\s*[:：]\s*(.+)$", cleaned, re.MULTILINE)
        if m_title:
            title = m_title.group(1).strip()

        # 2) Try labeled content anywhere
        m_content = re.search(
            r"^\s*本文\s*(?:\((?:Markdown|markdown)\))?\s*[:：]\s*\n(.*)$",
            cleaned,
            re.DOTALL | re.MULTILINE,
        )
        if m_content:
            content = m_content.group(1).strip()

        # 3) If title missing, try first Markdown heading (# or ##)
        if not title:
            m_heading = re.search(r"^\s*#{1,3}\s+(.+)$", cleaned, re.MULTILINE)
            if m_heading:
                title = m_heading.group(1).strip()
                # If content not yet set, use text after the heading line
                if not content:
                    heading_line_end = cleaned.find('\n', m_heading.start())
                    after_heading = cleaned[heading_line_end + 1 :] if heading_line_end != -1 else ""
                    # Prefer an explicit content label after the heading if present
                    m_content2 = re.search(
                        r"^\s*本文\s*(?:\((?:Markdown|markdown)\))?\s*[:：]\s*\n(.*)$",
                        after_heading,
                        re.DOTALL | re.MULTILINE,
                    )
                    content = (m_content2.group(1).strip() if m_content2 else after_heading.strip())

        # 4) If content still missing but we had a labeled title, take remainder after that line
        if not content and m_title:
            title_line_end = cleaned.find('\n', m_title.end())
            remainder = cleaned[title_line_end + 1 :] if title_line_end != -1 else ""
            m_content3 = re.search(
                r"^\s*本文\s*(?:\((?:Markdown|markdown)\))?\s*[:：]\s*\n(.*)$",
                remainder,
                re.DOTALL | re.MULTILINE,
            )
            content = (m_content3.group(1).strip() if m_content3 else remainder.strip())

        # 5) Final cleanups
        if content:
            # Drop a stray leading label if still present
            content = re.sub(r"^\s*本文\s*(?:\((?:Markdown|markdown)\))?\s*[:：]\s*", "", content).strip()
            # If content starts with a heading equal to title, remove it
            lines = content.splitlines()
            if lines:
                first = lines[0].strip()
                if title and first.startswith('#') and title in first:
                    content = "\n".join(lines[1:]).strip()
            # Collapse excessive blank-only lines at edges
            content = "\n".join([ln.rstrip() for ln in content.split('\n')]).strip()

        # 6) Fallbacks if any piece is still missing
        if not title:
            for line in cleaned.splitlines():
                s = line.strip()
                if not s or re.match(r"^\s*本文", s):
                    continue
                if s.startswith('#'):
                    title = re.sub(r"^\s*#{1,6}\s*", "", s).strip()
                else:
                    title = s
                break

        if not content:
            # Prefer explicit content label if present
            m_content4 = re.search(
                r"^\s*本文\s*(?:\((?:Markdown|markdown)\))?\s*[:：]\s*\n(.*)$",
                cleaned,
                re.DOTALL | re.MULTILINE,
            )
            if m_content4:
                content = m_content4.group(1).strip()
            else:
                # Use the whole text minus the first title line if applicable
                lines = cleaned.splitlines()
                if lines:
                    if title and lines[0].strip().lstrip('#').strip() == title:
                        content = "\n".join(lines[1:]).strip()
                    else:
                        content = "\n".join(lines).strip()

        if title and content:
            return title, content

        logger.warning(
            "LLMのレスポンス形式が不正です。タイトルまたは本文を抽出できませんでした。レスポンス先頭: %s...",
            response[:200],
        )
        return None


ContentEnhancerClaude4 = ContentEnhancerLLM
__all__ = ["ContentEnhancerLLM", "ContentEnhancerClaude4"]

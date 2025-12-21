import re
import json
from typing import List, Dict, Any, Optional, Tuple

class BlogSelectorProcess:
    """
    Pure process logic for Blog Selection.
    Handles command parsing, prompt creation, and response parsing.
    No IO, no DB, no API calls.
    """

    @staticmethod
    def parse_commands(texts: List[str]) -> Tuple[List[str], Optional[str], Optional[str], List[str]]:
        """
        Parses texts for commands (!Keyword, @Repost, #Style).
        Returns:
            cleaned_texts: List[str] - Texts with commands removed
            command_keyword: Optional[str] - Explicit blog selection keyword (!)
            repost_keyword: Optional[str] - Repost keyword (@)
            style_prompts: List[str] - Style instructions (#)
        """
        cleaned_texts = []
        command_keyword = None
        repost_keyword = None
        style_prompts = []

        if not texts:
            return [], None, None, []

        for text in texts:
            text_stripped = text.strip()

            # 1. Style Instruction (#)
            # Support both half-width # and full-width ＃
            # Skip URLs
            style_match = re.match(r"^[#＃](.+)", text_stripped, re.DOTALL)
            if style_match and not text_stripped.startswith("#http") and not text_stripped.startswith("＃http"):
                style_instruction = style_match.group(1).strip()
                if style_instruction:
                    style_prompts.append(style_instruction)
                continue

            # 2. Explicit Blog Selection (!)
            command_match = re.match(r"^!(\S+)(.*)", text_stripped, re.DOTALL)
            if command_match:
                if not command_keyword:  # First one wins
                    command_keyword = command_match.group(1)

                remaining = command_match.group(2).strip()
                if "#" in remaining:
                    parts = remaining.split("#", 1)
                    if parts[1].strip():
                        style_prompts.append(parts[1].strip())
                elif remaining:
                    cleaned_texts.append(remaining)
                continue

            # 3. Repost/Rewrite (@)
            repost_match = re.match(r"^@(\S*)(.*)", text_stripped, re.DOTALL)
            if repost_match:
                # If we already have a repost keyword, we ignore subsequent ones?
                # Or maybe we just take the first one. Logic mimics original:
                # "is_repost_mode = True"
                target_keyword = repost_match.group(1)
                remaining = repost_match.group(2).strip()

                # Treat empty keyword as generic repost (True)
                # But we return the keyword string (empty string if generic)
                if repost_keyword is None:
                    repost_keyword = target_keyword if target_keyword else ""

                if "#" in remaining:
                    parts = remaining.split("#", 1)
                    prompt_part = parts[1].strip()
                    if prompt_part:
                        style_prompts.append(prompt_part)
                elif remaining:
                     # If text after @ but no #, and no keyword, it's a prompt
                     if not target_keyword and remaining:
                         style_prompts.append(remaining)

                continue

            # Normal text
            cleaned_texts.append(text)

        return cleaned_texts, command_keyword, repost_keyword, style_prompts

    @staticmethod
    def filter_blogs(blogs: Dict[str, Any], content_text: str) -> Dict[str, Any]:
        """
        Filters out blogs that have exclude_keywords matching the content.
        Also filters out invalid/placeholder blogs.
        """
        # First filter invalid
        valid_blogs = {}
        for bid, cfg in blogs.items():
            hatena_id = cfg.get('hatena_id')
            hatena_blog_id = cfg.get('hatena_blog_id')
            api_key = cfg.get('hatena_api_key') or cfg.get('api_key')

            # Simple validation logic
            def is_valid(val):
                return val and str(val).strip() != '' and not str(val).lower().startswith('default')

            if is_valid(hatena_id) and is_valid(hatena_blog_id) and is_valid(api_key):
                valid_blogs[bid] = cfg

        if not content_text:
            return valid_blogs

        content_lower = content_text.lower()
        filtered = {}

        for bid, cfg in valid_blogs.items():
            exclude_keywords = cfg.get('exclude_keywords', [])
            if not exclude_keywords:
                filtered[bid] = cfg
                continue

            has_excluded = False
            for keyword in exclude_keywords:
                if keyword.lower() in content_lower:
                    has_excluded = True
                    break

            if not has_excluded:
                filtered[bid] = cfg

        return filtered

    @staticmethod
    def create_selection_prompt(content_text: str, image_descriptions: List[str], blogs: Dict[str, Any]) -> str:
        """Creates the LLM prompt for blog selection."""
        blog_options = []
        for blog_id, blog_config in blogs.items():
            keywords = blog_config.get('keywords', [])
            keywords_text = f"キーワード: {', '.join(keywords)}" if keywords else "キーワード: なし"
            exclude_keywords = blog_config.get('exclude_keywords', [])
            exclude_text = f"除外キーワード: {', '.join(exclude_keywords)}" if exclude_keywords else "除外キーワード: なし"
            blog_info = f"""
ID: {blog_id}
ブログ名: {blog_config.get('blog_name', 'Unknown')}
説明: {blog_config.get('description', 'No description')}
{keywords_text}
{exclude_text}
"""
            blog_options.append(blog_info.strip())

        blogs_text = "\n\n".join(blog_options)

        prompt = f"""あなたは、ブログ投稿先を選択するアシスタントです。
以下のコンテンツを分析して、最も適切なブログを選択してください。

【投稿内容】
テキスト:
{content_text}

画像情報:
{'; '.join(filter(None, image_descriptions))}

【利用可能なブログ】
{blogs_text}

【選択方法】
1. コンテンツのテーマ・キーワードと各ブログのキーワードを照合
2. ブログの説明文とコンテンツの内容の関連性を評価
3. **除外キーワードが含まれるブログは絶対に選択しない**
4. 最も多くのキーワードが一致するか、テーマが近いブログを選択

【重要な注意事項】
- 各ブログの「除外キーワード」に該当する内容が含まれている場合、そのブログは候補から除外してください
- 例: コンテンツに「家族」「子育て」が含まれる場合、除外キーワードに「家族」「子育て」があるブログは選択不可

コンテンツの内容を分析し、最も適切なブログのIDを選択してください。
以下のJSON形式で出力してください：

{{
  "blog_id": "選択したブログのID",
  "reason": "選択理由（キーワードマッチ数やテーマの関連性、除外判定など、100文字以内）"
}}

※必ず「ID: 」として記載されているIDの1つを選択してください。
出力はJSONのみ。先頭や末尾に説明文やコードブロック記号は付けないでください。
"""
        return prompt

    @staticmethod
    def parse_selection_response(response_text: str, available_blog_ids: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Parses the LLM response to extract blog_id and reason.
        Returns (blog_id, reason).
        """
        def extract_json(text):
            try: return json.loads(text)
            except: pass

            fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
            if fenced:
                try: return json.loads(fenced.group(1))
                except: pass

            brace_match = re.search(r"\{[\s\S]*?\}", text)
            if brace_match:
                if 'blog_id' in brace_match.group(0):
                    try: return json.loads(brace_match.group(0))
                    except: pass

            match = re.search(r"blog_id\"?\s*[:=]\s*\"([^\"]+)\"", text, re.IGNORECASE)
            if match: return {"blog_id": match.group(1)}
            return None

        parsed = extract_json(response_text)
        if not parsed:
            return None, None

        selected_id = parsed.get('blog_id')
        reason = parsed.get('reason')

        # Validation/Resolution logic
        if not selected_id:
            return None, None

        # Normalize and find in available_ids
        # (Assuming available_blog_ids are the keys from the dict used in prompt)
        # Note: The original code had complex resolution logic (matching name/hatena_id).
        # Ideally, that logic belongs here in Process if we pass the full config map,
        # or simplified if we expect LLM to behave.
        # Let's keep it simple: return the raw ID, let the Task resolve it if it's fuzzy?
        # Or better, pass the lookup map here.

        return str(selected_id).strip(), reason

    @staticmethod
    def resolve_blog_id(selected_id: str, all_blogs: Dict[str, Any]) -> Optional[str]:
        """Resolves a potentially fuzzy blog ID to a concrete key in all_blogs."""
        if not selected_id:
            return None

        if selected_id in all_blogs:
            return selected_id

        # Normalize
        norm = lambda s: (s or '').strip().lower()
        s_norm = norm(selected_id)

        for bid, cfg in all_blogs.items():
            if s_norm in {norm(cfg.get('hatena_blog_id')), norm(cfg.get('blog_name')), norm(cfg.get('line_channel_id'))}:
                return bid

        # URL check
        url_host = re.search(r"https?://([^/]+)", selected_id)
        if url_host:
            host = url_host.group(1).lower()
            # Handle hatenablog.com subdomains specifically if needed, or just match host
            # Usually hatena_blog_id is the subdomain part or full host?
            # Config usually has 'my-blog' for 'my-blog.hatenablog.com'
            host_part = host.split('.')[0] # Try subdomain

            for bid, cfg in all_blogs.items():
                if norm(cfg.get('hatena_blog_id')) == host or norm(cfg.get('hatena_blog_id')) == host_part:
                    return bid

        return None

    @staticmethod
    def create_keyword_selection_prompt(keyword: str, blogs: Dict[str, Any]) -> str:
        """Creates prompt for !Keyword selection."""
        blog_options = []
        for blog_id, blog_config in blogs.items():
            keywords = blog_config.get('keywords', [])
            keywords_text = f"Keywords: {', '.join(keywords)}" if keywords else ""
            blog_info = f"ID: {blog_id} | Name: {blog_config.get('blog_name')} | {keywords_text}"
            blog_options.append(blog_info)
        blogs_text = "\n".join(blog_options)

        prompt = f"""
あなたはブログ振り分けシステムです。ユーザーから「投稿先ブログの指定」を受けました。
以下の【指定キーワード】の意味を解釈し、【利用可能なブログ】の中から最も関連性の高いものを1つ選んでください。

【指定キーワード】
"{keyword}"

【利用可能なブログ】
{blogs_text}

【選択ルール】
1. キーワードがブログ名、説明、または関連語句と一致・連想されるものを選ぶ。
2. 例: "forex" -> FXブログ, "旅" -> 旅行ブログ
3. 該当するブログがない場合は、最も汎用的なブログを選んでください。

出力は以下のJSON形式のみ：
{{ "blog_id": "選択したID", "reason": "理由" }}
"""
        return prompt

    @staticmethod
    def heuristic_select(content_text: str, blogs: Dict[str, Any]) -> Optional[str]:
        """Heuristic selection based on keyword counting."""
        text = (content_text or '').lower()
        best_id = None
        best_score = 0

        for bid, cfg in blogs.items():
            keywords = cfg.get('keywords') or []
            if not isinstance(keywords, list):
                continue
            score = 0
            for kw in keywords:
                k = (kw or '').strip().lower()
                if not k: continue
                score += text.count(k)

            if score > best_score:
                best_score = score
                best_id = bid

        if best_id is None and blogs:
            return next(iter(blogs.keys()))

        return best_id

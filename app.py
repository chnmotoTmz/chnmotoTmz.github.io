import os
import sys
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import yaml
import requests
import base64
import json
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from xml.etree import ElementTree as ET

# Gemini API key (used by affiliate_linker for keyword extraction only)
EDITOR_GEMINI_KEY = "AIzaSyDiNnrPSs83gdu-PQb7qDPQqR1ZioPiDZo"

# Initialize CustomAPIClient from lib/llm.py (uses localhost:3000/api/ask)
from lib.llm import CustomAPIClient
llm_client = CustomAPIClient()

# Load environment variables
load_dotenv(".env.production")

app = Flask(__name__)
# Enable CORS for the Vite frontend (running on port 5173 by default)
CORS(app, resources={r"/api/*": {"origins": "*"}})

BLOGS_YML_PATH = "blogs.yml"

HATENA_NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'app': 'http://www.w3.org/2007/app',
}

# Register namespaces for output
ET.register_namespace('', 'http://www.w3.org/2005/Atom')
ET.register_namespace('app', 'http://www.w3.org/2007/app')


def load_blogs_config():
    """Load and parse the blogs.yml file, resolving environment variables."""
    if not os.path.exists(BLOGS_YML_PATH):
        return {}
    
    with open(BLOGS_YML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        for key, value in os.environ.items():
            if value:
                content = content.replace(f"${{{key}}}", value)
            
        try:
            config = yaml.safe_load(content)
            return config.get('blogs', {})
        except yaml.YAMLError as e:
            print(f"Error parsing blogs.yml: {e}")
            return {}


def get_blog_auth(blog_id):
    """Get Basic Auth credentials for a given blog_id."""
    blogs = load_blogs_config()
    blog = blogs.get(blog_id)
    if not blog:
        return None, None
    hatena_id = blog.get('hatena_id')
    api_key = blog.get('hatena_api_key')
    return hatena_id, api_key


def hatena_request(blog_id, path, method='GET', data=None):
    """Make an authenticated request to the Hatena AtomPub API."""
    hatena_id, api_key = get_blog_auth(blog_id)
    if not hatena_id or not api_key:
        return None, "Blog not found or missing credentials"
    
    if path.startswith('http'):
        base_url = path
    else:
        blogs = load_blogs_config()
        hatena_blog_id = blogs[blog_id].get('hatena_blog_id')
        base_url = f"https://blog.hatena.ne.jp/{hatena_id}/{hatena_blog_id}/atom{path}"
    
    try:
        response = requests.request(
            method,
            base_url,
            auth=(hatena_id, api_key),
            data=data,
            headers={'Content-Type': 'application/atom+xml; charset=utf-8'},
            timeout=15
        )
        response.raise_for_status()
        return response, None
    except requests.exceptions.RequestException as e:
        return None, str(e)


@app.route('/api/blogs', methods=['GET'])
def get_blogs():
    """Returns the list of available blogs from blogs.yml (excluding sensitive API keys)."""
    blogs_data = load_blogs_config()
    
    # Strip out API keys before sending to frontend
    safe_blogs = {}
    for blog_id, data in blogs_data.items():
        safe_data = {k: v for k, v in data.items() 
                     if not k.endswith('_api_key') and k != 'hatena_api_key'}
        safe_blogs[blog_id] = safe_data
        
    return jsonify({"blogs": safe_blogs})


@app.route('/api/posts/<blog_id>', methods=['GET'])
def get_posts(blog_id):
    """Fetch recent posts for a given blog via Hatena AtomPub API."""
    response, error = hatena_request(blog_id, '/entry')
    if error:
        return jsonify({"error": error}), 400
    
    try:
        root = ET.fromstring(response.content)
        posts = []
        for entry in root.findall('atom:entry', HATENA_NS):
            title_el = entry.find('atom:title', HATENA_NS)
            id_el = entry.find('atom:id', HATENA_NS)
            updated_el = entry.find('atom:updated', HATENA_NS)
            content_el = entry.find('atom:content', HATENA_NS)
            
            # Get the edit link
            edit_link = ''
            for link in entry.findall('atom:link', HATENA_NS):
                if link.get('rel') == 'edit':
                    edit_link = link.get('href', '')
                    break
            
            # Get draft status
            app_control = entry.find('app:control', HATENA_NS)
            is_draft = False
            if app_control is not None:
                draft_el = app_control.find('app:draft', HATENA_NS)
                if draft_el is not None and draft_el.text == 'yes':
                    is_draft = True
            
            posts.append({
                'id': id_el.text if id_el is not None else '',
                'title': title_el.text if title_el is not None else '(No Title)',
                'updated': updated_el.text if updated_el is not None else '',
                'content': content_el.text if content_el is not None else '',
                'edit_link': edit_link,
                'is_draft': is_draft,
            })
        
        return jsonify({"posts": posts})
    except ET.ParseError as e:
        return jsonify({"error": f"XML parse error: {str(e)}"}), 500

@app.route('/api/search', methods=['GET'])
def search_all_blogs():
    """Search for a keyword across all configured blogs in parallel."""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify({"error": "No search query provided"}), 400

    blogs = load_blogs_config()
    all_results = []
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def fetch_blog_posts(target_blog_id, target_blog_info):
        results = []
        next_url = '/entry'
        page_count: int = 0
        max_pages: int = 5 # 最大5ページ(約50件)に制限して負荷を下げる
        import time
        
        while next_url and page_count < max_pages:
            response, error = hatena_request(target_blog_id, next_url)
            if error:
                print(f"[{target_blog_id}] Fetch error on page {page_count}: {error}")
                break
            
            try:
                root = ET.fromstring(response.content)
                for entry in root.findall('atom:entry', HATENA_NS):
                    title_el = entry.find('atom:title', HATENA_NS)
                    content_el = entry.find('atom:content', HATENA_NS)
                    
                    title_text = title_el.text if (title_el is not None and title_el.text) else ''
                    content_text = content_el.text if (content_el is not None and content_el.text) else ''
                    
                    # Check if query is in title or content
                    if query in title_text.lower() or query in content_text.lower():
                        id_el = entry.find('atom:id', HATENA_NS)
                        updated_el = entry.find('atom:updated', HATENA_NS)
                        
                        edit_link = ''
                        for link in entry.findall('atom:link', HATENA_NS):
                            if link.get('rel') == 'edit':
                                edit_link = link.get('href', '')
                                break
                        
                        app_control = entry.find('app:control', HATENA_NS)
                        is_draft = False
                        if app_control is not None:
                            draft_el = app_control.find('app:draft', HATENA_NS)
                            if draft_el is not None and draft_el.text == 'yes':
                                is_draft = True
                        
                        results.append({
                            'blog_id': target_blog_id,
                            'blog_name': target_blog_info.get('blog_name', target_blog_id),
                            'id': id_el.text if id_el is not None else '',
                            'title': title_text or '(No Title)',
                            'updated': updated_el.text if updated_el is not None else '',
                            'content': content_text,
                            'edit_link': edit_link,
                            'is_draft': is_draft,
                        })
                
                # Check for next page
                next_url = None
                for link in root.findall('atom:link', HATENA_NS):
                    if link.get('rel') == 'next':
                        next_url = str(link.get('href'))
                        break
                        
                page_count = int(page_count) + 1
                time.sleep(0.5) # API負荷軽減のためのスリープ
                
            except ET.ParseError:
                print(f"[{target_blog_id}] XML Parse Error on page {page_count}")
                break
            
        return results

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_blog = {}
        for b_id, b_info in blogs.items():
            if b_info.get('hatena_id') and b_info.get('hatena_api_key'):
                future = executor.submit(fetch_blog_posts, str(b_id), b_info)
                future_to_blog[future] = str(b_id)
        
        for future in as_completed(future_to_blog):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                # Log error but continue with other blogs
                print(f"Error fetching from blog: {e}")

    # Sort results by updated date descending
    all_results.sort(key=lambda x: x.get('updated', ''), reverse=True)
    
    return jsonify({"results": all_results})


@app.route('/api/posts/<blog_id>', methods=['POST'])
def save_post(blog_id):
    """Create or update a blog post via Hatena AtomPub API."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    title = data.get('title', '')
    content = data.get('content', '')
    is_draft = data.get('is_draft', True)
    edit_link = data.get('edit_link', '')  # If editing existing post
    
    blogs = load_blogs_config()
    blog = blogs.get(blog_id)
    if not blog:
        return jsonify({"error": "Blog not found"}), 404
    
    hatena_id = blog.get('hatena_id')
    
    import html
    
    draft_val = 'yes' if is_draft else 'no'
    escaped_title = html.escape(title)
    escaped_content = html.escape(content)
    escaped_hatena_id = html.escape(hatena_id)
    
    atom_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{escaped_title}</title>
  <author><name>{escaped_hatena_id}</name></author>
  <content type="text/x-hatena-syntax">{escaped_content}</content>
  <app:control>
    <app:draft>{draft_val}</app:draft>
  </app:control>
</entry>"""
    
    xml_bytes = atom_xml.encode('utf-8')
    
    if edit_link:
        # Update existing entry
        try:
            _, api_key = get_blog_auth(blog_id)
            response = requests.put(
                edit_link,
                auth=(hatena_id, api_key),
                data=xml_bytes,
                headers={'Content-Type': 'application/atom+xml; charset=utf-8'},
                timeout=15
            )
            response.raise_for_status()
            return jsonify({"success": True, "action": "updated"})
        except requests.exceptions.RequestException as e:
            return jsonify({"error": str(e)}), 500
    else:
        # Create new entry
        response, error = hatena_request(blog_id, '/entry', method='POST', data=xml_bytes)
        if error:
            return jsonify({"error": error}), 500
        
        # Parse response to get the new post URL
        try:
            root = ET.fromstring(response.content)
            edit_link_el = ''
            for link in root.findall('atom:link', HATENA_NS):
                if link.get('rel') == 'edit':
                    edit_link_el = link.get('href', '')
                    break
            return jsonify({"success": True, "action": "created", "edit_link": edit_link_el})
        except ET.ParseError:
            return jsonify({"success": True, "action": "created"})


@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Upload an image to Imgur and return the URL."""
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    imgur_client_id = os.environ.get('IMGUR_CLIENT_ID')
    
    if not imgur_client_id:
        return jsonify({"error": "IMGUR_CLIENT_ID not configured"}), 500
    
    try:
        img_data = file.read()
        img_b64 = base64.b64encode(img_data).decode('utf-8')
        
        response = requests.post(
            'https://api.imgur.com/3/image',
            headers={'Authorization': f'Client-ID {imgur_client_id}'},
            data={'image': img_b64, 'type': 'base64'},
            timeout=30
        )
        result = response.json()
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "url": result['data']['link'],
                "delete_hash": result['data']['deletehash']
            })
        else:
            return jsonify({"error": result.get('data', {}).get('error', 'Imgur upload failed')}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/improve', methods=['POST'])
def improve_post():
    """Use Gemini API to improve a blog post based on a given instruction type."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    title = data.get('title', '')
    content = data.get('content', '')
    instruction_type = data.get('instruction_type', 'monetize')
    custom_prompt = data.get('custom_prompt', '')

    presets = {
        'structure': """あなたはプロの編集者です。以下のブログ記事について、本文の独自の主張やニュアンスは【一切変えずに】、読みやすい構造への整理のみを行ってください。

構造化のルール：
・H1（記事タイトル）：メインキーワードとサブキーワードを含める
・冒頭文（サマリー）：最初の150文字以内で記事概要とキーワードを含める
・H2見出し：最大4つ程度に整理し、前半にキーワードを配置。必要に応じてH3を活用。

改善方針：
1. ファーストビュー：冒頭に「この記事でわかること（箇条書き）」と「読了目安時間（例: 3分）」を追記。
2. セクション分割の整理：H2が連続する場合はH3で整理し、1セクションを短く保つ（スキャナビリティ向上）。「よくある質問」セクションをH2で追加（リッチスニペット対策）。

※禁止事項※
【絶対に】架空のリンク（はてなフォトライフの [f:id:...] やURL）を生成しないでください。
【絶対に】「読者登録」や「X(Twitter)のフォロー」を促す文面を勝手に追加しないでください。
絶対に記事の元のトピックや主張の内容、言葉のニュアンスを変えないこと。フォーマットと構造の整理のみを行うこと。""",

        'monetize': """あなたはプロのブログコンサルタントです。以下のはてなブログ記事をマネタイズ強化の観点で改善してください。
改善方針：
1. 冒頭で読者の具体的な悩み・損失を明示する
2. 抽象的な文章に具体例・数値・テンプレートを追加する
3. 記事末尾に強いCTAを追加する
4. スクリーンショットされやすい「刺さる一文」を太字で挿入する
5. タイトルを検索流入と感情トリガーを意識したものに変更する""",

        'sns': """あなたはSNSバズを専門とするコンテンツマーケターです。以下の記事をSNS拡散最適化してください。
改善方針：
1. 拡散されやすい「名言系の一文」を太字で作る
2. 冒頭で「この記事を読む価値」を明確にする
3. 箇条書きを活用して可読性を上げる
4. 「保存必須」などのフレーズを入れる
5. ハッシュタグ候補を記事末尾に追加する""",

        'seo': """あなたはSEOの専門家です。以下の記事を検索上位表示を狙って改善してください。
改善方針：
1. タイトルに主要キーワードを前半に配置する（32文字以内）
2. 冒頭の100文字以内に記事の要約とキーワードを含める
3. 見出し（##）を質問形式に変更する
4. 関連キーワードを本文中に追加する
5. まとめセクションにFAQ形式を追加する""",

        'readability': """あなたはプロのライター・編集者です。以下の記事を読みやすさ重視で改善してください。
改善方針：
1. 1段落を最大4行以内に収める
2. 難しい表現を平易な言葉に置き換える
3. 接続詞を見直す
4. 重要なポイントは箇条書きや太字で強調する
5. 構成を「問題解決」の順に整える""",

        'title': """あなたはコピーライターです。以下の記事タイトルを改善し、タイトルのみ5案提案し、最もおすすめのものを本文冒頭に反映してください。
タイトル改善の観点：
1. 検索されやすいキーワードを前半に配置
2. 数字・具体性を入れる
3. 読者の悩みに訴えかける
4. 32文字以内を目安に""",
    }

    if custom_prompt:
        system_prompt = custom_prompt
    else:
        system_prompt = presets.get(instruction_type, presets['monetize'])

    full_prompt = f"""{system_prompt}

※共通の禁止事項※
1. 【絶対に】架空のリンクURLや架空のプレースホルダー（例: `[f:id:...]` などの画像タグや、`[読者になる]`等のSNSフォローボタン）を勝手に生成・追加しないでください。事実に基づくテキストのみ出力してください。
2. 記事本文で元々言及されていない商品を勝手に「おすすめ商品」としてアフィリエイト風に紹介しないでください。

---
【元のタイトル】
{title}

【元の本文（はてな記法）】
{content}
---

改善後の記事を以下のJSON形式で返してください。はてな記法はそのまま維持してください：

{{
  "title": "改善後のタイトル",
  "content": "改善後の本文"
}}

JSONのみを返してください。"""

    try:
        result = llm_client.generate(full_prompt)
        if not result.success or not result.text:
            return jsonify({"error": result.error or "LLMからの応答がありません"}), 500

        # Extract JSON from LLM response
        json_match = re.search(r'\{.*\}', result.text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            improved_title = parsed.get("title", title)
            improved_content = parsed.get("content", content)
        else:
            improved_title = title
            improved_content = result.text

        # Fix dead links (e.g. [text](#)) generated by AI
        from lib.fact_checker import cleanup_fact_references
        improved_content = cleanup_fact_references(improved_title, improved_content)

        # Add real affiliate links (replace AI-hallucinated ones)
        from lib.affiliate_linker import add_affiliate_links
        improved_content = add_affiliate_links(improved_title, improved_content)

        return jsonify({
            "success": True,
            "title": improved_title,
            "content": improved_content,
        })

    except Exception as e:
        return jsonify({"error": f"Improvement error: {str(e)}"}), 500


@app.route('/api/optimize_all', methods=['POST'])
def optimize_all():
    """One-click optimization: LLM Improve -> FactCheck -> Affiliate Linker."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    title = data.get('title', '')
    content = data.get('content', '')

    system_prompt = """あなたはプロの編集者・マーケターです。以下の記事を最高品質の状態に全自動で最適化してください。

改善方針：
1. 【タイトル】検索流入を狙い、32文字以内で魅力的なタイトルにする。数字や具体性を入れる。
2. 【SEO・読みやすさ】冒頭で記事の要約・悩みの解決を提示する。見出し（##）や箇条書きを使って可読性を上げる。
3. 【SNS・拡散】シェアされやすい「刺さる一文」を太字で入れる。
4. 【構造】文脈を整え、1段落を短くし平易な文章にする。"""

    full_prompt = f"""{system_prompt}

---
【元のタイトル】
{title}

【元の本文（はてな記法・Markdown）】
{content}
---

改善後の記事を以下のJSON形式で返してください。元の記法は維持してください。

{{
  "title": "改善後のタイトル",
  "content": "改善後の本文"
}}

JSONのみを返してください。"""

    try:
        # 1. LLM Optimization via CustomAPIClient (localhost:3000/api/ask)
        result = llm_client.generate(full_prompt)
        if result.success and result.text:
            json_match = re.search(r'\{.*\}', result.text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                new_title = parsed.get("title", title)
                new_content = parsed.get("content", content)
            else:
                new_title = title
                new_content = result.text
        else:
            new_title = title
            new_content = content

        # 2. Fact Check Cleanup
        from lib.fact_checker import cleanup_fact_references
        checked_content = cleanup_fact_references(new_title, new_content)

        # 3. Affiliate Links (real products from Rakuten API)
        from lib.affiliate_linker import add_affiliate_links
        final_content = add_affiliate_links(new_title, checked_content)

        return jsonify({
            "success": True,
            "title": new_title,
            "content": final_content,
        })

    except Exception as e:
        return jsonify({"error": f"Optimization error: {str(e)}"}), 500


@app.route('/api/tools/affiliate', methods=['POST'])
def auto_affiliate():
    """Use the newly extracted lib.rakuten_api logic without LLM hallucinations."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    title = data.get('title', '')
    content = data.get('content', '')

    try:
        from lib.affiliate_linker import add_affiliate_links
        
        enhanced_content = add_affiliate_links(title, content)
        
        return jsonify({
            "success": True,
            "content": enhanced_content
        })
    except Exception as e:
        return jsonify({"error": f"Affiliate insertion failed: {str(e)}"}), 500


@app.route('/api/tools/factcheck', methods=['POST'])
def auto_factcheck():
    """Use the newly extracted lib.fact_checker to resolve real URLs."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    title = data.get('title', '')
    content = data.get('content', '')

    try:
        from lib.fact_checker import cleanup_fact_references
        
        enhanced_content = cleanup_fact_references(title, content)
        
        return jsonify({
            "success": True,
            "content": enhanced_content
        })
    except Exception as e:
        return jsonify({"error": f"Fact Check cleanup failed: {str(e)}"}), 500


@app.route('/api/tools/thumbnail', methods=['POST'])
def auto_thumbnail():
    """Generates a thumbnail and inserts it into the content."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    title = data.get('title', '')
    content = data.get('content', '')

    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400

    try:
        from lib.thumbnail_task import ThumbnailGeneratorTask
        
        # Initialize task with enabled=True
        task = ThumbnailGeneratorTask({"enabled": True})
        
        # Use title as the default prompt for image generation
        result = task.execute({
            "title": title,
            "content": content,
            "thumbnail_prompt": title
        })
        
        return jsonify({
            "success": True,
            "content": result.get("enhanced_content", content)
        })
    except Exception as e:
        return jsonify({"error": f"Thumbnail generation failed: {str(e)}"}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    # Run the server on port 5000
    app.run(debug=True, use_reloader=False, port=5000)

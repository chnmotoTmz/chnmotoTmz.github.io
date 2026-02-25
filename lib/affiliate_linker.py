"""
アフィリエイトリンク挿入モジュール。
AI改善後の記事に対し、楽天APIで実商品を検索して挿入する。
AIが生成した偽アフィリエイトセクションは除去して差し替える。
"""
import re
import json
import logging
from typing import List, Optional
from lib import rakuten_api

logger = logging.getLogger(__name__)


def extract_keywords_from_content(title: str, content: str) -> List[str]:
    """
    CustomAPIClient (localhost:3000/api/ask) を使って
    記事から商品検索キーワードを抽出する。
    フォールバック: タイトルからの簡易抽出
    """
    try:
        from lib.llm import CustomAPIClient
        client = CustomAPIClient()

        prompt = f"""以下のブログ記事から、楽天市場で検索すべき商品キーワードを3〜5個抽出してください。

【記事タイトル】
{title}

【本文（冒頭500文字）】
{content[:500]}

JSON形式で返してください: {{"keywords": ["キーワード1", "キーワード2"]}}
JSONのみを返してください。"""

        result = client.generate(prompt)
        if result.success and result.text:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result.text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                keywords = parsed.get('keywords', [])
                if keywords:
                    logger.info(f"Extracted keywords: {keywords}")
                    return keywords[:5]
    except Exception as e:
        logger.warning(f"AI keyword extraction failed: {e}")

    # Fallback: simple keyword extraction from title
    logger.info("Using fallback keyword extraction from title")
    # Remove common Japanese particles and split
    clean_title = re.sub(r'[「」【】『』（）()!！?？、。]', ' ', title)
    words = [w.strip() for w in clean_title.split() if len(w.strip()) >= 2]
    return words[:3] if words else [title]


def remove_ai_affiliate_section(content: str) -> str:
    """AIが生成した偽アフィリエイト/商品推薦セクションを除去する。"""
    patterns = [
        # 🛒 おすすめ関連商品 section
        r'\n*##\s*🛒\s*おすすめ関連商品[\s\S]*?(?=\n##\s[^#]|\n#\s[^#]|\Z)',
        # 🔗 links section with fake links
        r'\n*###?\s*🔗[^\n]*\n[\s\S]*?(?=\n##\s[^#]|\n#\s[^#]|\Z)',
        # Generic "おすすめ商品" placeholder
        r'\n*おすすめ商品が現在こちらの[\s\S]*?(?=\n##|\n#|\Z)',
        # Rakuten placeholder link
        r'\n*\[楽天市場で商品を探す\]\(https://www\.rakuten\.co\.jp/category/\)\s*',
        # 📢 読者登録のお願い section
        r'\n*##?\s*📢\s*読者登録のお願い[\s\S]*?(?=\n##\s[^#]|\n#\s[^#]|\Z)',
        r'\n*📢\s*読者登録のお願い[\s\S]*?(?=\n##\s[^#]|\n#\s[^#]|\Z)',
        # Fake Hatena image links generated as placeholders
        r'\[f:id:[^\]]+\][^\n]*',
    ]
    for pattern in patterns:
        content = re.sub(pattern, '', content)
    return content.rstrip() + '\n'


def build_affiliate_section(products: list) -> str:
    """実際の楽天商品データからアフィリエイトセクションを構築する。"""
    if not products:
        return ''

    section = "\n\n---\n\n## 🛒 この記事に関連するおすすめ商品\n\n"
    for i, product in enumerate(products[:3], 1):
        name = product.get('itemName', '商品')
        price = product.get('itemPrice', 0)
        url = product.get('affiliate_url', product.get('itemUrl', ''))
        img = product.get('imageUrl', '')

        section += f"### {i}. {name}\n\n"
        if img:
            section += f"[![{name}]({img})]({url})\n\n"
        section += f"**価格**: ¥{price:,}\n\n"
        section += f"[👉 詳細を見る・購入する]({url})\n\n"
        if i < min(len(products), 3):
            section += "---\n\n"

    return section


def add_affiliate_links(title: str, content: str) -> str:
    """
    記事にアフィリエイトリンクを追加する。
    1. AIの偽アフィリエイトセクションを除去
    2. CustomAPIClientでキーワード抽出
    3. 楽天APIで実商品検索
    4. 実データでセクションを構築して挿入
    """
    try:
        # 1. Remove AI-generated fake affiliate sections
        content = remove_ai_affiliate_section(content)

        # 2. Extract keywords
        keywords = extract_keywords_from_content(title, content)
        logger.info(f"Searching products for: {keywords}")

        # 3. Search Rakuten API
        products = rakuten_api.search_related_products(
            {"title": title},
            keywords=keywords
        )

        # 4. Build and append real affiliate section
        if products:
            section = build_affiliate_section(products)
            content += section
            logger.info(f"Added {len(products)} products to article")
        else:
            logger.warning("No products found from Rakuten API")

        return content

    except Exception as e:
        logger.error(f"Affiliate linker failed: {e}")
        return content

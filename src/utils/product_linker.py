import re
from typing import Dict, Optional

def insert_product_links(text: str, product_links: Dict[str, str]) -> str:
    """
    検出した[商品詳細：商品名はこちら]表現を、product_links辞書に基づきMarkdownリンクに変換。
    product_links: {商品名: URL}
    URLが無い場合は注記を挿入。
    """
    def replacer(match):
        product = match.group(1).strip()
        url = product_links.get(product)
        if url:
            return f"[商品詳細：{product}はこちら]({url})"
        else:
            return f"[商品詳細：{product}はこちら（URL未設定）]"
    return re.sub(r"\[商品詳細：(.+?)はこちら\]", replacer, text)

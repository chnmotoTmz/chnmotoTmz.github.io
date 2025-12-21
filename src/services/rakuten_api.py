# -*- coding: utf-8 -*-
"""
Rakuten API integration module.
"""

import requests
import os
import json
import logging
import time
from typing import List, Dict, Union, Optional, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID")

def search_products(keyword: str, application_id: Optional[str] = None, max_retries: int = 3) -> Union[List[Dict], Dict]:
    app_id_to_use = application_id or RAKUTEN_APP_ID
    if not app_id_to_use:
        return {"status": "error", "message": "RAKUTEN_APP_ID missing."}

    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
    params = {
        "format": "json",
        "keyword": keyword,
        "applicationId": app_id_to_use,
        "hits": 5,
        "sort": "standard"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 429:
                time.sleep((attempt + 1) * 5)
                continue
            response.raise_for_status()
            data = response.json()

            if "Items" in data and data["Items"]:
                return [
                    {
                        "itemName": item.get("Item", {}).get("itemName"),
                        "itemPrice": item.get("Item", {}).get("itemPrice"),
                        "itemUrl": item.get("Item", {}).get("itemUrl"),
                        "itemCode": item.get("Item", {}).get("itemCode"),
                        "imageUrl": (item.get("Item", {}).get("mediumImageUrls", [{}])[0] or {}).get("imageUrl")
                    }
                    for item in data["Items"] if isinstance(item, dict)
                ]
            return []
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep((attempt + 1) * 3)
            else:
                return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "Max retries exceeded"}

def generate_affiliate_link(item_url: str, affiliate_id: Optional[str] = None) -> str:
    aff_id = affiliate_id or RAKUTEN_AFFILIATE_ID
    if not aff_id or not item_url: return item_url
    return f"https://hb.afl.rakuten.co.jp/hgc/{aff_id}/?pc={quote(item_url)}&m=http%3A%2F%2Fm.rakuten.co.jp%2F"

def search_related_products(concept: Dict[str, Any], keywords: Optional[List[str]] = None, gemini_service=None) -> List[Dict]:
    search_keywords = keywords[:5] if keywords else []
    if concept.get('keywords'): search_keywords.extend(concept.get('keywords', [])[:3])
    
    unique_keywords = list(dict.fromkeys([k.strip() for k in search_keywords if k.strip()]))
    if not unique_keywords: return []

    all_products = []
    for i, keyword in enumerate(unique_keywords[:3]):
        try:
            if i > 0: time.sleep(1)
            products = search_products(keyword)
            if isinstance(products, list):
                for j, product in enumerate(products[:2]):
                    product['affiliate_url'] = generate_affiliate_link(product.get('itemUrl'))
                    all_products.append(product)
        except: continue
    return all_products[:5]
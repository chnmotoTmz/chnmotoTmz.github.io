# -*- coding: utf-8 -*-
"""
Rakuten API integration module (Standalone version)
"""

import requests
import os
import json
import logging
import time
from typing import List, Dict, Union, Optional, Any
from urllib.parse import quote
import random

logger = logging.getLogger(__name__)

RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID")

def search_products(keyword: str, application_id: Optional[str] = None, max_retries: int = 5) -> Union[List[Dict], Dict]:
    """Search Rakuten Ichiba for a keyword with exponential backoff and jitter."""
    app_id_to_use = application_id or os.getenv("RAKUTEN_APP_ID")
    if not app_id_to_use:
        logger.warning("RAKUTEN_APP_ID is not set; cannot search.")
        return {"status": "error", "message": "RAKUTEN_APP_ID missing."}

    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
    params = {
        "format": "json",
        "keyword": keyword,
        "applicationId": app_id_to_use,
        "hits": 5,
        "sort": "standard"
    }

    backoff_base = 1.0
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 429:
                sleep_for = backoff_base * (2 ** attempt) + random.random()
                time.sleep(sleep_for)
                continue
            response.raise_for_status()

            try:
                data = response.json()
            except ValueError as e:
                return {"status": "error", "message": "Invalid JSON from Rakuten"}

            if "Items" in data and data["Items"]:
                results = []
                for item in data["Items"]:
                    itm = item.get("Item", {}) if isinstance(item, dict) else {}
                    results.append({
                        "itemName": itm.get("itemName"),
                        "itemPrice": itm.get("itemPrice"),
                        "itemUrl": itm.get("itemUrl"),
                        "itemCode": itm.get("itemCode"),
                        "imageUrl": (itm.get("mediumImageUrls", [{}])[0] or {}).get("imageUrl")
                    })
                return results

            return []
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                sleep_for = backoff_base * (2 ** attempt) + random.random()
                time.sleep(sleep_for)
                continue
            return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "Max retries exceeded"}

def generate_affiliate_link(item_url: str, affiliate_id: Optional[str] = None) -> str:
    aff_id = affiliate_id or os.getenv("RAKUTEN_AFFILIATE_ID")
    if not aff_id or not item_url: return item_url
    return f"https://hb.afl.rakuten.co.jp/hgc/{aff_id}/?pc={quote(item_url)}&m=http%3A%2F%2Fm.rakuten.co.jp%2F"

def _tokenize_keyword(k: str) -> List[str]:
    import re
    return [t for t in re.split(r"[^\w一-龥ぁ-んァ-ン]+", k) if t]

def search_related_products(concept: Dict[str, Any], keywords: Optional[List[str]] = None) -> List[Dict]:
    candidate_keywords = []
    if keywords: candidate_keywords.extend(keywords[:5])
    if concept.get('keywords'): candidate_keywords.extend(concept.get('keywords', [])[:5])
    if concept.get('title'): candidate_keywords.append(concept.get('title'))

    expanded = []
    for k in candidate_keywords:
        if not k or not isinstance(k, str): continue
        k = k.strip()
        expanded.append(k)
        tokens = _tokenize_keyword(k)
        if len(tokens) >= 2: expanded.append(" ".join(tokens[-2:]))
        expanded.extend(tokens[:3])

    seen = set()
    unique_queries = []
    for q in expanded:
        if not q: continue
        normalized = q.strip().lower()
        if normalized in seen: continue
        seen.add(normalized)
        unique_queries.append(q.strip())

    if not unique_queries: return []

    all_products = []
    for idx, q in enumerate(unique_queries[:8]):
        try:
            if idx > 0: time.sleep(0.5)
            products = search_products(q)
            if isinstance(products, dict) and products.get('status') == 'error': continue
            if isinstance(products, list) and products:
                for p in products:
                    p['affiliate_url'] = generate_affiliate_link(p.get('itemUrl') or '')
                    all_products.append(p)
            if len(all_products) >= 5: break
        except Exception:
            continue

    seen_keys = set()
    uniq = []
    for p in all_products:
        key = p.get('itemUrl') or p.get('itemCode') or json.dumps(p, ensure_ascii=False)
        if key in seen_keys: continue
        seen_keys.add(key)
        uniq.append(p)
    return uniq[:5]

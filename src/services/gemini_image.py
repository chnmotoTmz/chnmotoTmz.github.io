#!/usr/bin/env python3
"""
Gemini互換APIから画像を取得するためのモジュール。
"""

import os
from pathlib import Path
import requests
import json
from typing import Optional

def get_gemini_image(prompt: str, api_url: str = "http://localhost:3000/api/ask", bearer: Optional[str] = None, timeout: int = 180, mode: Optional[str] = None, new_chat: bool = False) -> Optional[str]:
    """
    Gemini互換APIにプロンプトを送信し、画像URLを取得する。
    APIレスポンス形式: { status: "success", answer: { requestId, text, images: [...] } }
    images配列要素: { src?: string, base64?: string, downloaded?: boolean, filename?: string }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    
    # 新しいAPI形式のリクエストボディ
    body = {
        "prompt": prompt,
        "requestId": "gemini_image_request"
    }
    # Optional mode/new_chat fields
    if mode:
        body['mode'] = mode
    if new_chat:
        body['new_chat'] = True
    
    try:
        logger.info(f"Gemini API呼び出し: {api_url}")
        resp = requests.post(api_url, json=body, timeout=timeout, headers=headers)
        logger.info(f"APIレスポンスステータス: {resp.status_code}")
        
        if resp.status_code != 200:
            logger.warning(f"APIエラー: {resp.text}")
            return None
        
        try:
            data = resp.json()
            logger.info(f"APIレスポンス: {data}")
        except Exception as e:
            logger.warning(f"JSONパースエラー: {e}")
            return None
        
        # 新しいレスポンス形式からimagesを取得
        answer = data.get('answer', {})
        images = answer.get('images', [])
        logger.info(f"画像配列: {images}")

        if not images:
            logger.warning("画像が見つかりません")
            return None

        # APIのベースURL（/api/ask を除いた部分）を取得して、/downloads/filename を公開URLに変換するために使用
        try:
            api_base = api_url.rsplit('/', 1)[0]
        except Exception:
            api_base = api_url

        # 最初の画像候補を処理
        first = images[0]
        if isinstance(first, dict):
            # 1) サーバーが保存したファイル名が返される場合 -> 公開URLに変換して返す
            filename = first.get('filename')
            downloaded = first.get('downloaded')
            if filename and (downloaded or filename.startswith('/')):
                # filename 例: "/downloads/gemini_image_xxx.png"
                # api_base が http://localhost:3000 の場合、公開URL を構築
                if filename.startswith('/'):
                    url = api_base + filename
                else:
                    # もしかして '/downloads/..' でない場合は直接結合
                    url = api_base + '/' + filename.lstrip('/')
                logger.info(f"サーバー保存ファイルの公開URL取得: {url}")
                return url

            # 2) base64 があれば優先的にデコードして一時ファイルへ保存して返す
            if 'base64' in first and first['base64']:
                import base64
                import tempfile
                base64_data = first['base64']
                # data URL のプレフィックスを除去
                if isinstance(base64_data, str) and base64_data.startswith('data:'):
                    try:
                        _, encoded = base64_data.split(',', 1)
                    except ValueError:
                        encoded = base64_data
                else:
                    encoded = base64_data
                img_data = base64.b64decode(encoded)
                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp.write(img_data)
                    tmp_path = tmp.name
                logger.info(f"Base64画像を一時ファイルに保存: {tmp_path}")
                return tmp_path

            # 3) 外部 src があればそのまま返す（呼び出し側でダウンロード可能）
            if 'src' in first and first['src']:
                url = first['src']
                logger.info(f"画像URL取得: {url}")
                return url

        # 画像要素が文字列のケース
        if isinstance(first, str):
            logger.info(f"画像URL取得 (str): {first}")
            return first

        logger.warning("有効な画像データが見つかりません")
        return None
        
    except Exception as e:
        logger.error(f"Gemini API呼び出しエラー: {e}")
        return None

def find_latest_image(local_dir: str) -> Optional[str]:
    """
    指定ディレクトリから最新の画像ファイルパスを返す。
    """
    folder = os.path.abspath(local_dir)
    if not os.path.isdir(folder):
        return None
    allowed_exts = {'.png', '.jpg', '.jpeg', '.webp'}
    candidates = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext in allowed_exts:
            candidates.append((path, os.path.getmtime(path)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]
#!/usr/bin/env python3
"""
Chrome経由でカスタムAPIをテストするスクリプト
"""

import os
import sys
import logging
import requests

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 環境変数読み込み
from env_loader import load
load()

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_chrome_api_endpoint():
    """Chrome経由APIエンドポイントテスト"""
    logger.info("Chrome経由APIエンドポイントテスト開始")

    # FastAPIサーバーが起動している前提
    endpoint_url = "http://localhost:8000/api/chrome/gemini-image"
    
    bearer = os.getenv('CUSTOM_THUMBNAIL_API_BEARER')

    # テストプロンプト
    data = {
        "prompt": "美しい山の風景を描いた画像を生成してください。",
        "bearer": bearer
    }

    try:
        # エンドポイント呼び出し
        response = requests.post(endpoint_url, json=data, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('image_url'):
                logger.info(f"テスト成功: 画像URLを取得しました: {result['image_url']}")
                print(f"生成された画像URL: {result['image_url']}")
            else:
                logger.error("テスト失敗: レスポンスにimage_urlが含まれていません")
                print("失敗: 画像URLが取得できませんでした")
        else:
            logger.error(f"テスト失敗: HTTP {response.status_code}, {response.text}")
            print(f"失敗: HTTP {response.status_code}")

    except Exception as e:
        logger.error(f"テスト中にエラー発生: {e}", exc_info=True)
        print(f"エラー: {e}")

if __name__ == "__main__":
    test_chrome_api_endpoint()
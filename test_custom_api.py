#!/usr/bin/env python3
"""
コマンドラインからカスタムLLM APIの画像生成をテストするスクリプト

使い方:
  python test_custom_api.py

必要な環境変数 (.env.production など):
  - CUSTOM_THUMBNAIL_API_URL
  - CUSTOM_THUMBNAIL_API_BEARER (任意)

このスクリプトは、カスタムAPIに対してPOSTを行い、レスポンスがJSONの場合は
"""

import os
import sys
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 環境変数読み込み
from env_loader import load
load()

from src.services.gemini_image import get_gemini_image

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_custom_api():
    """カスタムAPIの画像生成テスト"""
    logger.info("カスタムAPIテスト開始")

    api_url = os.getenv('CUSTOM_THUMBNAIL_API_URL')
    if not api_url:
        logger.error("CUSTOM_THUMBNAIL_API_URLが設定されていません")
        return

    bearer = os.getenv('CUSTOM_THUMBNAIL_API_BEARER')

    # テストプロンプト
    prompt = "美しい山の風景を描いた画像を生成してください。"

    try:
        # API呼び出し
        # Request an image generation; mark new_chat=True to start fresh conversation when testing
        result = get_gemini_image(prompt, api_url, bearer, timeout=180, mode='image', new_chat=True)

        if result:
            if os.path.isfile(result):
                logger.info(f"テスト成功: 画像ファイルを取得しました: {result}")
                print(f"生成された画像ファイル: {result}")
            else:
                logger.info(f"テスト成功: 画像URLを取得しました: {result}")
                print(f"生成された画像URL: {result}")
        else:
            logger.error("テスト失敗: 結果が取得できませんでした")
            print("失敗: 画像が生成されませんでした")

    except Exception as e:
        logger.error(f"テスト中にエラー発生: {e}", exc_info=True)
        print(f"エラー: {e}")

if __name__ == "__main__":
    test_custom_api()
#!/usr/bin/env python3
"""
カスタムAPI経由のサムネイル生成テストスクリプト（直接URLダウンロード版）
"""

import os
import sys
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 環境変数読み込み
from env_loader import load
load()

from src.services.thumbnail_generator_service import ThumbnailGeneratorService

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_custom_api_with_folder_monitoring():
    """フォルダ監視を使ったカスタムAPIテスト"""
    logger.info("カスタムAPI（フォルダ監視版）テスト開始")

    # サービス初期化
    service = ThumbnailGeneratorService()

    # テストプロンプト
    prompt = "美しい山の風景を描いた画像を生成してください。"

    try:
        # カスタムAPIで画像生成
        result_url = service._generate_via_custom_api(prompt, os.getenv('CUSTOM_THUMBNAIL_API_URL'))

        if result_url:
            logger.info(f"テスト成功: Imgur URL = {result_url}")
            print(f"生成された画像URL: {result_url}")
        else:
            logger.error("テスト失敗: 画像URLが取得できませんでした")
            print("失敗: 画像が生成されませんでした")

    except Exception as e:
        logger.error(f"テスト中にエラー発生: {e}", exc_info=True)
        print(f"エラー: {e}")

if __name__ == "__main__":
    test_custom_api_with_folder_monitoring()
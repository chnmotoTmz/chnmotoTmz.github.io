#!/usr/bin/env python3
"""
コマンドラインからカスタムLLM APIの画像生成をテストするスクリプト
"""

import os
import sys
from pathlib import Path
import requests
import json

# リポジトリのsrcをインポート可能にする
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from src.services.thumbnail_generator_service import ThumbnailGeneratorService

def test_api_response():
    """APIのレスポンスを直接確認し、画像URLを返す"""
    custom_api_url = os.getenv('CUSTOM_THUMBNAIL_API_URL')
    if not custom_api_url:
        print("❌ CUSTOM_THUMBNAIL_API_URL が設定されていません")
        return None

    test_prompt = "A beautiful sunset over mountains with vibrant colors"
    image_prompt = f"以下のプロンプトで画像を1枚生成してください。生成した画像はダウンロードしてください。\n\n{test_prompt}"

    print(f"🌐 API URL: {custom_api_url}")
    print(f"📝 送信プロンプト: {image_prompt}")

    try:
        headers = {"Content-Type": "application/json"}
        bearer = os.getenv('CUSTOM_THUMBNAIL_API_BEARER')
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        
        # ブラウザのようなUser-Agentを追加
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

        resp = requests.post(
            custom_api_url,
            json={"prompt": image_prompt},
            timeout=300,  # タイムアウトを300秒に
            headers=headers,
        )

        print(f"📡 ステータスコード: {resp.status_code}")
        print(f"📄 レスポンスヘッダー: {dict(resp.headers)}")

        if resp.status_code == 200:
            try:
                body = resp.json()
                print(f"📦 レスポンスボディ: {json.dumps(body, indent=2, ensure_ascii=False)}")

                # imagesの確認
                images = body.get('answer', {}).get('images', [])
                if images:
                    print(f"🖼️ 検出された画像数: {len(images)}")
                    for i, img in enumerate(images):
                        print(f"  画像{i+1}: {img}")
                        src = img.get('src')
                        if src:
                            print(f"    src URL: {src}")
                            return src  # 最初の画像URLを返す
                else:
                    print("❌ images フィールドが見つかりません")

            except json.JSONDecodeError as e:
                print(f"❌ JSONパースエラー: {e}")
                print(f"📄 生レスポンス: {resp.text[:500]}")
        else:
            print(f"❌ API呼び出し失敗: {resp.text[:500]}")

    except Exception as e:
        print(f"❌ リクエストエラー: {e}")
    
    return None

def main():
    # 環境変数をロード
    load_dotenv('.env.production')

    print("=== APIレスポンス確認 ===")
    image_url = test_api_response()
    
    if not image_url:
        print("❌ 画像URLが取得できませんでした")
        return

    print(f"\n=== ステップ2: 画像ダウンロード ===")
    print(f"📥 ダウンロード対象URL: {image_url}")
    
    # ステップ2a: /api/download でbase64を取得
    try:
        custom_api_url = os.getenv('CUSTOM_THUMBNAIL_API_URL')
        # /api/download は /api/ask とは別のエンドポイント
        base_url = custom_api_url.rsplit('/', 1)[0]  # /api/ask の /api を取得
        download_url = base_url + '/download'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/json'
        }
        
        download_resp = requests.post(download_url, json={'url': image_url}, headers=headers, timeout=60)
        print(f"📡 /api/download ステータス: {download_resp.status_code}")
        
        if download_resp.status_code == 200:
            try:
                download_data = download_resp.json()
                print(f"📦 ダウンロードレスポンス: {json.dumps(download_data, indent=2)}")
                
                if download_data.get('success'):
                    base64_data = download_data.get('base64')
                    if base64_data:
                        print("✅ base64データが取得できました")
                        print(f"📊 base64サイズ: {len(base64_data)} 文字")
                        
                        # base64をデコードして保存
                        import base64
                        if base64_data.startswith('data:'):
                            header, encoded = base64_data.split(',', 1)
                            image_data = base64.b64decode(encoded)
                        else:
                            image_data = base64.b64decode(base64_data)
                        
                        import time
                        timestamp = int(time.time() * 1000)
                        test_image_path = f"test_image_{timestamp}.png"
                        with open(test_image_path, 'wb') as f:
                            f.write(image_data)
                        print(f"💾 テスト画像を保存しました: {test_image_path}")
                        print(f"📊 画像データサイズ: {len(image_data)} bytes")
                    else:
                        print("❌ base64データが空です")
                else:
                    print(f"❌ ダウンロードAPIが失敗を返しました: {download_data}")
            except Exception as e:
                print(f"❌ JSONパースエラー: {e}")
                print(f"📄 生レスポンス: {download_resp.text[:500]}")
        else:
            print(f"❌ /api/download 呼び出し失敗: {download_resp.status_code}")
            print(f"📄 エラーレスポンス: {download_resp.text[:500]}")
            
    except Exception as e:
        print(f"❌ ダウンロードエラー: {e}")
        import traceback
        traceback.print_exc()

   

if __name__ == "__main__":
    main()
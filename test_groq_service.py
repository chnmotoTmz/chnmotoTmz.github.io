#!/usr/bin/env python3
"""
Groqサービステストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 環境変数読み込み
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.production')

from src.services.groq_service import GroqService
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

def test_groq_service():
    """Groqサービスをテスト"""
    print("🔍 Groqサービステスト開始")

    try:
        # サービス初期化
        groq_service = GroqService()
        print("✅ Groqサービス初期化成功")

        # 接続テスト
        print("🔗 接続テスト中...")
        if groq_service.test_connection():
            print("✅ 接続テスト成功")
        else:
            print("❌ 接続テスト失敗")
            return

        # テキスト生成テスト
        print("📝 テキスト生成テスト中...")
        prompt = "日本の首都はどこですか？ 簡潔に答えてください。"
        result = groq_service.generate_text(prompt, max_tokens=100, temperature=0.1)
        print(f"📄 生成結果: {result}")

        # もう一つのテスト
        print("📝 追加テスト中...")
        prompt2 = "Pythonの特徴を3つ挙げてください。"
        result2 = groq_service.generate_text(prompt2, max_tokens=200, temperature=0.5)
        print(f"📄 生成結果: {result2}")

        print("🎉 全てのテスト成功！")

    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_groq_service()
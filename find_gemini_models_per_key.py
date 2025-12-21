#!/usr/bin/env python3
"""
各APIキーごとに利用可能なGeminiモデル一覧を取得し、利用可能なモデル名を表示する
"""
import os
import google.generativeai as genai

# .env.productionからAPIキーを取得
api_keys = os.environ.get("GEMINI_API_KEYS", "").split(",")
api_keys = [k.strip() for k in api_keys if k.strip()]

print("=== Gemini APIキーごとの利用可能モデル一覧 ===\n")

for idx, key in enumerate(api_keys):
    print(f"--- APIキー {idx+1}/{len(api_keys)} --- (先頭8文字: {key[:8]})")
    try:
        genai.configure(api_key=key)
        models = genai.list_models()
        for m in models:
            # 生成系のみ表示
            if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods:
                print(f"  - {m.name}")
    except Exception as e:
        print(f"  ❌ モデル一覧取得失敗: {e}")
    print()
print("\n上記リストから使えるモデル名をGEMINI_MODELに設定してください。")

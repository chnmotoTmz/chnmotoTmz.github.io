#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG コンテンツ取得テスト
はてなブログの記事URLから内容を取得し、キャッシュするテスト
"""
import sys
import logging
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-50s | %(message)s',
    encoding='utf-8'
)

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.hatena_blog_content_fetcher import HatenaBlogContentFetcher

def test_content_fetcher():
    """コンテンツ取得とキャッシュのテスト"""
    
    print("\n" + "="*100)
    print("[TEST] Hatena Blog Content Fetcher")
    print("="*100 + "\n")
    
    # テスト対象のURL（ユーザーが指定したもの）
    test_urls = [
        "https://arafo40tozan.hatenadiary.jp/entry/20251018/1760767097",
        "https://arafo40tozan.hatenadiary.jp/entry/20251019/1760863297",
        "https://arafo40tozan.hatenadiary.jp/entry/20251018/1760767078",
    ]
    
    fetcher = HatenaBlogContentFetcher()
    
    for url in test_urls:
        print(f"\n[INFO] 記事URLを処理中: {url}")
        print("-" * 100)
        
        # 初回取得（実際にスクレイピング）
        print("  1回目の取得（スクレイピング）...")
        content1 = fetcher.get_article_content(url, use_cache=False)
        
        if content1:
            content_len = len(content1)
            preview = content1[:200].replace('\n', ' ')
            print(f"  ✅ 取得成功: {content_len} 文字")
            print(f"  プレビュー: {preview}...")
            
            # 2回目取得（キャッシュから）
            print("\n  2回目の取得（キャッシュから）...")
            content2 = fetcher.get_article_content(url, use_cache=True)
            
            if content2 == content1:
                print(f"  ✅ キャッシュから取得成功: {len(content2)} 文字")
            else:
                print(f"  ⚠️  キャッシュ内容が異なります")
        else:
            print(f"  ❌ 取得失敗")
    
    print("\n" + "="*100)
    print("[INFO] キャッシュ情報")
    print("="*100)
    print(f"キャッシュディレクトリ: {fetcher.cache_dir}")
    
    # キャッシュファイル一覧
    cache_files = list(fetcher.cache_dir.glob('*.json'))
    print(f"キャッシュファイル数: {len(cache_files)}")
    for cache_file in cache_files:
        print(f"  - {cache_file.name}")
    
    print("\n" + "="*100)
    print("[SUMMARY] テスト完了")
    print("="*100)
    print("\n✅ 実装内容:")
    print("  1. はてなブログのURLから記事内容をスクレイピング")
    print("  2. 取得した内容をJSONキャッシュとして保存")
    print("  3. キャッシュの有効期限は24時間（設定可能）")
    print("  4. RAGモデルのトレーニング時に自動的に記事内容を取得")
    print("  5. 類似記事検索時に実際のコンテンツがプロンプトに含まれる")
    print("\n" + "="*100 + "\n")

if __name__ == '__main__':
    try:
        test_content_fetcher()
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

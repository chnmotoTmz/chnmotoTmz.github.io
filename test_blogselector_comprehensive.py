#!/usr/bin/env python3
"""
完全なBlogSelector動作テスト
異なるコンテンツで複数のブログを選択して、ID=1 以外が選ばれるか確認
"""

import os
import sys
import logging

# 環境設定
os.environ["LLM_PROVIDER"] = "gemini"
os.environ["GEMINI_API_KEY"] = "AIzaSyDJIcN4YCiC3AEvLLdp-D7rYJlh8I7oQr8"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s'
)
logger = logging.getLogger(__name__)

from src.services.tasks.blog_selector_task import BlogSelectorTask
from src.blog_config import BlogConfig

def test_blog_selector():
    """BlogSelector がコンテンツに基づいて異なるブログを選択するかテスト"""
    
    logger.info("=" * 100)
    logger.info("BLOG SELECTOR FIX VERIFICATION TEST")
    logger.info("=" * 100)
    
    # 利用可能なブログを確認
    all_blogs = BlogConfig.get_all_blogs()
    logger.info(f"\n📚 Available blogs ({len(all_blogs)}):")
    for blog_id, config in list(all_blogs.items())[:5]:
        logger.info(f"  - {blog_id}: {config.get('blog_name')} (keywords: {config.get('keywords', [])})")
    
    # BlogSelector初期化
    task = BlogSelectorTask({})
    logger.info(f"\n✅ BlogSelectorTask initialized (provider: {task.llm_service.provider.value})")
    
    # テストケース1: 登山関連コンテンツ
    logger.info("\n" + "=" * 100)
    logger.info("TEST 1: 登山関連コンテンツ")
    logger.info("=" * 100)
    
    test_inputs_1 = {
        "texts": [
            "先週末、六甲山にハイキングに行きました。天気も良く、最高の景色が見えました。"
        ],
        "images_for_prompt": []
    }
    
    result_1 = task.execute(test_inputs_1)
    blog_name_1 = result_1.get("blog_config", {}).get("name", "Unknown")
    blog_id_1 = result_1.get("blog_config", {}).get("id", "Unknown")
    logger.info(f"✅ Selected blog: {blog_name_1} (ID: {blog_id_1})")
    
    # テストケース2: 技術・ガジェット関連
    logger.info("\n" + "=" * 100)
    logger.info("TEST 2: 技術・ガジェット関連コンテンツ")
    logger.info("=" * 100)
    
    test_inputs_2 = {
        "texts": [
            "新しいMacBook Pro M4を購入しました。GPUの性能がかなり向上しているのが感じられます。"
        ],
        "images_for_prompt": []
    }
    
    result_2 = task.execute(test_inputs_2)
    blog_name_2 = result_2.get("blog_config", {}).get("name", "Unknown")
    blog_id_2 = result_2.get("blog_config", {}).get("id", "Unknown")
    logger.info(f"✅ Selected blog: {blog_name_2} (ID: {blog_id_2})")
    
    # テストケース3: 外国語学習関連
    logger.info("\n" + "=" * 100)
    logger.info("TEST 3: 言語学習関連コンテンツ")
    logger.info("=" * 100)
    
    test_inputs_3 = {
        "texts": [
            "今日の中国語レッスンで、新しい単語を100個学びました。発音がとても難しいです。"
        ],
        "images_for_prompt": []
    }
    
    result_3 = task.execute(test_inputs_3)
    blog_name_3 = result_3.get("blog_config", {}).get("name", "Unknown")
    blog_id_3 = result_3.get("blog_config", {}).get("id", "Unknown")
    logger.info(f"✅ Selected blog: {blog_name_3} (ID: {blog_id_3})")
    
    # 結果検証
    logger.info("\n" + "=" * 100)
    logger.info("VERIFICATION")
    logger.info("=" * 100)
    
    results = [
        ("テスト1 (登山)", blog_name_1, blog_id_1),
        ("テスト2 (ガジェット)", blog_name_2, blog_id_2),
        ("テスト3 (言語学習)", blog_name_3, blog_id_3),
    ]
    
    for test_name, blog_name, blog_id in results:
        logger.info(f"{test_name}: {blog_name} (ID: {blog_id})")
    
    # チェック：複数の異なるブログが選ばれたか？
    blog_ids = [blog_id_1, blog_id_2, blog_id_3]
    unique_blogs = len(set(blog_ids))
    
    if unique_blogs >= 2:
        logger.info(f"\n✅ SUCCESS: {unique_blogs}個の異なるブログが選ばれました（ID=1以外も含む）")
        logger.info("✅ BlogSelector は正常に機能しています！")
        return True
    else:
        logger.warning(f"\n⚠️  WARNING: 全て同じブログが選ばれました (ID: {blog_ids[0]})")
        logger.warning("⚠️  BlogSelector の結果がまだ限定的かもしれません")
        return False

if __name__ == "__main__":
    try:
        success = test_blog_selector()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)

"""
RAGサマリー生成のテスト
Web/YouTube サマリー生成のテスト
"""
import logging
logging.basicConfig(level=logging.INFO)

from src.services.tasks.rag_similar_articles_fetcher import RagSimilarArticlesFetcher

def test_summary_generation():
    """サマリー生成のテスト"""
    fetcher = RagSimilarArticlesFetcher({})
    
    # テスト用の記事
    test_title = "AIの基礎を学ぶ"
    test_content = """
    人工知能（AI）は、私たちの生活を大きく変えつつあります。
    機械学習やディープラーニングの進歩により、AIはますます賢くなっています。
    
    この記事では、AIの基本的な概念から、実際の応用例まで幅広く解説します。
    特に、ChatGPTやClaudeなどの大規模言語モデルについても触れていきます。
    
    AIの歴史は1950年代に遡ります。アラン・チューリングが「機械は思考できるか」
    という問いを投げかけたことから始まりました。
    
    現在、AIは画像認識、自然言語処理、自動運転など様々な分野で活用されています。
    """
    
    summary = fetcher._generate_article_summary(test_title, test_content)
    print(f"\n=== RAGサマリー生成テスト ===")
    print(f"タイトル: {test_title}")
    print(f"本文: {len(test_content)}文字")
    print(f"生成されたサマリー: {summary}")
    print(f"サマリー文字数: {len(summary)}")
    

def test_contextual_keywords():
    """文脈キーワード生成のテスト"""
    from src.services.rakuten_api import _get_contextual_keywords
    from src.services.gemini_service import GeminiService
    
    gemini = GeminiService()
    
    # テストケース1: ニュース系記事
    concept1 = {
        'genre': 'ニュース',
        'theme': 'レアアース供給問題と日本の対応',
        'keywords': ['レアアース', '中国', '供給', 'EV', '電気自動車']
    }
    
    result1 = _get_contextual_keywords(concept1, concept1['keywords'], gemini)
    print(f"\n=== 文脈キーワード生成テスト ===")
    print(f"ジャンル: {concept1['genre']}")
    print(f"テーマ: {concept1['theme']}")
    print(f"元キーワード: {concept1['keywords']}")
    print(f"生成キーワード: {result1}")


def test_web_summary():
    """Webサマリー生成のテスト"""
    from src.services.tasks.web_summary_fetcher_task import WebSummaryFetcher
    
    fetcher = WebSummaryFetcher({})
    
    # テスト用のURL（軽いページ）
    test_urls = ["https://www.python.org/about/"]
    
    print(f"\n=== Webサマリー生成テスト ===")
    print(f"URL: {test_urls[0]}")
    
    result = fetcher.execute({"web_links": test_urls})
    summaries = result.get("web_summaries", [])
    
    for s in summaries:
        print(f"タイトル: {s.get('title', 'N/A')}")
        print(f"LLM要約: {s.get('summary', 'N/A')}")
        print(f"要約文字数: {len(s.get('summary', ''))}")


if __name__ == "__main__":
    print("=" * 50)
    print("サマリー生成テスト")
    print("=" * 50)
    
    test_summary_generation()
    test_contextual_keywords()
    test_web_summary()

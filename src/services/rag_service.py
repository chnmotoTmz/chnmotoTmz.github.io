"""
RAG（Retrieval-Augmented Generation）機能関連サービス。

このモジュールは、データベースから記事コンテンツを収集してRAGモデル用のコーパスを作成したり、
クエリに基づいて関連性の高い過去記事の情報を要約して提供する機能を持っています。
"""
import re
import os
import json
import logging
from typing import List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from src.database import db, Article
from src.services.gemini_service import GeminiService

# ロガーと設定の初期化
logger = logging.getLogger(__name__)
try:
    gemini_service = GeminiService()
except ValueError as e:
    logger.error(f"GeminiServiceの初期化に失敗しました。APIキーが設定されているか確認してください。: {e}")
    gemini_service = None

# 環境変数からRAGコンテキスト機能の有効/無効を決定
ENABLE_RAG_CONTEXT = os.getenv('ENABLE_RAG_CONTEXT', '0') == '1'
RAG_CONTEXT_MODEL_NAME = os.getenv('RAG_CONTEXT_MODEL_NAME', 'hatena_blog_entries')
RAG_CONTEXT_TOP_N = int(os.getenv('RAG_CONTEXT_TOP_N', '3'))
RAG_CONTEXT_SUMMARY_MAX_CHARS = int(os.getenv('RAG_CONTEXT_SUMMARY_MAX_CHARS', '350'))

# モジュールから公開する関数を明示
__all__ = ['collect_corpus', 'build_rag_context_bundle']

def _strip_html_for_rag(text: str) -> str:
    """RAGコーパス作成のために、HTMLタグや不要な空白を除去します。"""
    if not text:
        return ''
    # scriptとstyleタグを内容ごと除去
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 残りのHTMLタグを除去
    text = re.sub(r'<[^>]+>', ' ', text)
    # 連続する空白を一つにまとめる
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def collect_corpus() -> List[str]:
    """
    データベースから公開済みの記事を取得し、RAGモデル学習用のコーパスを生成します。
    各エントリは「URL: [URL]\n[本文]」の形式になります。
    """
    corpus = []
    try:
        # Flaskのアプリケーションコンテキストが必要な場合があるため、
        # with app.app_context() の中で呼び出すのがより安全です。
        # ここでは直接呼び出していますが、呼び出し元でのコンテキスト管理を想定しています。
        articles = Article.query.filter_by(published=True).order_by(Article.id.asc()).all()
        for article in articles:
            plain_content = _strip_html_for_rag(article.content)
            # 日本語の一人称を簡易的に除去
            plain_content = re.sub(r'私(は|が|を|に|の|も|へ)?', '', plain_content)
            plain_content = re.sub(r'\s+', ' ', plain_content).strip()
            corpus.append(f"URL:{article.hatena_url or ''}\n{plain_content}")
        logger.info(f"Successfully collected {len(corpus)} articles for RAG corpus.")
    except SQLAlchemyError as e:
        logger.error(f"Failed to collect RAG corpus due to a database error: {e}", exc_info=True)
        return [] # DBエラー時は空のリストを返す
    except Exception as e:
        logger.error(f"An unexpected error occurred during RAG corpus collection: {e}", exc_info=True)
        return []
    return corpus

def build_rag_context_bundle(query_text: str) -> str:
    """
    クエリテキストに類似する過去記事をRAGで検索し、
    それらの情報を時系列で要約したコンテキストを生成します。
    """
    if not ENABLE_RAG_CONTEXT or not gemini_service:
        return ''

    try:
        from src.rag import predict_with_model
    except ImportError:
        logger.warning("RAG context generation skipped: 'predict_with_model' could not be imported.")
        return ''

    try:
        base_query = (query_text or '')[:500]
        similar_results = predict_with_model(base_query, RAG_CONTEXT_MODEL_NAME, top_n=RAG_CONTEXT_TOP_N)

        if not similar_results:
            logger.info("No similar articles found for RAG context.")
            return ''

        # 類似記事の情報を整形し、DBから追加情報を取得
        normalized_articles = _normalize_similar_articles(similar_results)

        if not normalized_articles:
            return ''

        # 時系列順にソート
        normalized_articles.sort(key=lambda x: x['id'])

        # 要約プロンプトの生成
        summary_prompt = _create_summary_prompt(base_query, normalized_articles)

        # Geminiで要約を生成
        chrono_summary = gemini_service.generate_content(summary_prompt)
        if not chrono_summary:
            return ''

        # 最終的なコンテキストバンドルの組み立て
        return _assemble_context_bundle(chrono_summary, normalized_articles)

    except Exception as e:
        logger.error(f"Failed to build RAG context bundle: {e}", exc_info=True)
        return ''

def _normalize_similar_articles(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """類似検索結果を整形し、DBから追加情報を取得して正規化します。"""
    normalized = []
    for r in results:
        raw_text = (r.get('text') or '').strip()
        if not raw_text:
            continue

        # 'URL:'プレフィックスからURLと本文を分離
        parts = raw_text.split('\n', 1)
        url_line = parts[0]
        url_match = re.match(r'URL:\s*(\S+)', url_line)
        if not url_match:
            continue

        url = url_match.group(1)
        # DBから記事を検索
        article = Article.query.filter_by(hatena_url=url).first()

        if article:
            summary = _strip_html_for_rag(article.content)[:160]
            normalized.append({'id': article.id, 'title': article.title, 'summary': summary})
        else:
            # DBにない場合は、元のテキストから情報を抽出
            body_part = parts[1].strip() if len(parts) > 1 else ''
            title = body_part.split('\n')[0][:80] # 仮のタイトル
            summary = body_part[:160]
            normalized.append({'id': float('inf'), 'title': title, 'summary': summary}) # DBにないものは最後にソート

    return normalized

def _create_summary_prompt(base_query: str, articles: List[Dict[str, Any]]) -> str:
    """時系列要約を生成するためのプロンプトを作成します。"""
    article_lines = [f"{idx}. {art['title']} | {art['summary']}" for idx, art in enumerate(articles, 1)]
    chrono_block_src = '\n'.join(article_lines)

    return (
        "以下は現在の入力内容と関連度の高い過去記事の時系列断片（古い→新しい）です。\n"
        "各行は『番号. タイトル | サマリ』形式。これを読み:\n"
        "1) 時系列の流れと変遷\n2) 継続/蓄積しているテーマ\n3) 直近で未解決/進行中のポイント\n4) 今回入力への接続視点\nを200字以内で要約。\n"
        "禁止: 行頭の説明文/英語/重複羅列/本文丸写し。出力は要約段落のみ。\n"
        f"\n【現在入力(先頭500文字)】\n{base_query}\n\n【時系列断片】\n{chrono_block_src}\n"
    )

def _assemble_context_bundle(summary: str, articles: List[Dict[str, Any]]) -> str:
    """生成された要約と未解決ポイントから最終的なコンテキスト文字列を組み立てます。"""
    summary = summary.strip()[:RAG_CONTEXT_SUMMARY_MAX_CHARS]
    context_block = f"【関連時系列サマリ】\n{summary}\n"

    # 未解決ポイントの収集（この例では単純化のため省略）
    # 本来はDBの記事から関連情報を取得する

    logger.info(f"RAG context bundle generated successfully. Length: {len(context_block)}")
    return context_block

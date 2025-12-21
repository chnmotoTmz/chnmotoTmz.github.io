"""
RAG (Retrieval-Augmented Generation) 関連のAPIエンドポイント。

過去記事の検索、モデルの再学習、外部データソースとの同期など、
RAG機能に特化したAPIを提供します。
これらのエンドポイントは主に管理目的や、外部からの検索機能として利用されます。
"""
import re
import os
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError

# ロガーの設定
logger = logging.getLogger(__name__)
# RAG機能用のブループリントを作成
rag_bp = Blueprint('rag', __name__)

# --- エンドポイント定義 ---

@rag_bp.route('/rag/search', methods=['GET'])
def rag_search():
    """
    RAGモデルを使用して過去記事を検索し、結果の要約を返します。

    クエリパラメータ:
        q, query (str): 検索キーワード (必須)。
        k, top_n (int): 取得する結果の数 (任意、デフォルトは5)。

    Returns:
        JSON: 検索結果。成功時はURL、テキストスニペット、スコアのリスト。
    """
    # パラメータの取得とバリデーション
    query = (request.args.get('q') or request.args.get('query') or '').strip()
    if not query:
        return jsonify({'ok': False, 'error': 'Query parameter "q" is required.'}), 400

    try:
        top_k_raw = request.args.get('k') or request.args.get('top_n') or '5'
        top_k = int(top_k_raw)
    except ValueError:
        return jsonify({'ok': False, 'error': 'Invalid value for "k" or "top_n". Must be an integer.'}), 400

    # RAGモジュールの遅延インポート
    try:
        from src.rag import predict_with_model
    except ImportError as e:
        logger.error(f"Failed to import RAG module for search: {e}")
        return jsonify({'ok': False, 'error': 'RAG module not available.'}), 500

    # モデルによる予測の実行
    try:
        model_name = os.getenv('RAG_MODEL_NAME', 'hatena_blog_entries')
        raw_results = predict_with_model(query, model_name, top_n=top_k) or []

        results = []
        for r in raw_results:
            raw_text = (r.get('text') or '').strip()
            if not raw_text:
                continue

            # テキストからURLと本文を抽出
            url = ''
            body = raw_text
            if raw_text.startswith('URL:'):
                lines = raw_text.splitlines()
                if lines:
                    match = re.match(r'^URL:\s*(\S+)', lines[0])
                    if match:
                        url = match.group(1)
                        body = '\n'.join(lines[1:])

            # スニペットの生成
            body_clean = re.sub(r'[\s\u3000]+', ' ', re.sub(r'私[はがをも]*', '', body))
            snippet = body_clean[:160]

            results.append({
                'url': url,
                'text': snippet,
                'score': r.get('similarity')
            })

        return jsonify({'ok': True, 'query': query, 'count': len(results), 'results': results})
    except Exception as e:
        logger.exception("Error during RAG search execution.")
        return jsonify({'ok': False, 'error': 'Failed to perform search.'}), 500

@rag_bp.route('/rag/ping', methods=['GET'])
def rag_ping():
    """RAGサービスの死活監視用エンドポイント。"""
    return jsonify({'ok': True, 'service': 'rag', 'message': 'pong'})

@rag_bp.route('/rag/update', methods=['POST'])
def rag_update():
    """
    はてなブログからブログ記事を取得し、RAGモデルを更新します。
    
    このエンドポイントは、記事投稿後の手動更新や、
    外部からのWebhook経由での更新に使用できます。
    
    Returns:
        JSON: 更新結果。成功時はモデル情報を含む。
    """
    try:
        from src.services.blog_rag_service import blog_rag_service
    except ImportError as e:
        logger.error(f"Failed to import BlogRAGService: {e}")
        return jsonify({'ok': False, 'error': 'RAG service not available.'}), 500
    
    try:
        logger.info("RAGモデルの手動更新リクエストを受信しました。")
        success, message = blog_rag_service.update_blog_rag_model()
        
        if success:
            # モデルの状態を取得
            status = blog_rag_service.get_model_status()
            logger.info(f"✅ RAGモデル更新成功: {message}")
            
            return jsonify({
                'ok': True,
                'message': message,
                'model': {
                    'name': blog_rag_service.model_name,
                    'docs': status.get('docs', 0),
                    'features': status.get('features', 0),
                    'trained_at': status.get('trained_at', 'Unknown')
                }
            }), 200
        else:
            logger.error(f"❌ RAGモデル更新失敗: {message}")
            return jsonify({'ok': False, 'error': message}), 500
            
    except Exception as e:
        logger.exception("RAGモデル更新中に予期せぬエラーが発生しました。")
        return jsonify({'ok': False, 'error': 'An unexpected error occurred during RAG update.'}), 500

@rag_bp.route('/rag/status', methods=['GET'])
def rag_status():
    """
    RAGモデルの現在の状態を取得します。
    
    Returns:
        JSON: モデルの存在、ドキュメント数、最終学習日時など
    """
    try:
        from src.services.blog_rag_service import blog_rag_service
    except ImportError as e:
        logger.error(f"Failed to import BlogRAGService: {e}")
        return jsonify({'ok': False, 'error': 'RAG service not available.'}), 500
    
    try:
        status = blog_rag_service.get_model_status()
        
        if status.get('exists'):
            return jsonify({
                'ok': True,
                'model': {
                    'name': blog_rag_service.model_name,
                    'exists': True,
                    'docs': status.get('docs', 0),
                    'features': status.get('features', 0),
                    'trained_at': status.get('trained_at', 'Unknown')
                }
            }), 200
        else:
            return jsonify({
                'ok': True,
                'model': {
                    'name': blog_rag_service.model_name,
                    'exists': False,
                    'message': 'Model has not been trained yet.'
                }
            }), 200
            
    except Exception as e:
        logger.exception("RAGモデル状態取得中にエラーが発生しました。")
        return jsonify({'ok': False, 'error': 'Failed to get model status.'}), 500

@rag_bp.route('/rag/retrain', methods=['POST'])
def rag_retrain():
    """
    データベースから最新のコーパスを収集し、RAGモデルを再学習します。
    注意: このエンドポイントは管理用であり、認証が必要です。
    """
    model_name = os.getenv('RAG_MODEL_NAME', 'hatena_blog_entries')
    try:
        from src.services.rag_service import collect_corpus
        from src.rag import train_and_save_model
    except ImportError as e:
        logger.error(f"Failed to import modules for retraining: {e}")
        return jsonify({'ok': False, 'error': 'A module required for retraining is not available.'}), 500

    try:
        corpus = collect_corpus()
        logger.info(f"Corpus collected for retraining: {len(corpus)} entries.")
        if not corpus:
            return jsonify({'ok': False, 'error': 'Corpus is empty, nothing to train.'}), 400

        ok, msg = train_and_save_model(corpus, model_name)
        if not ok:
            logger.error(f"Model retraining failed: {msg}")
            return jsonify({'ok': False, 'error': msg}), 500

        logger.info(f"Model retraining successful: {msg}")
        return jsonify({'ok': True, 'model': model_name, 'entries': len(corpus), 'message': msg})
    except Exception as e:
        logger.exception("An unexpected error occurred during model retraining.")
        return jsonify({'ok': False, 'error': 'An unexpected error occurred.'}), 500

@rag_bp.route('/rag/sync_hatena', methods=['POST'])
def rag_sync_hatena():
    """
    はてなブログから全記事を取得し、データベースに新規記事のみを同期します。
    オプションで、同期後にモデルの再学習も実行可能です。
    注意: このエンドポイントは管理用であり、認証が必要です。
    """
    try:
        from src.services.hatena_service import HatenaService
        from src.database import db, Article
        from src.services.rag_service import collect_corpus
        from src.rag import train_and_save_model, needs_retrain
    except ImportError as e:
        logger.error(f"Failed to import modules for Hatena sync: {e}")
        return jsonify({'ok': False, 'error': 'A module required for sync is not available.'}), 500

    retrain = bool((request.get_json(silent=True) or {}).get('retrain', False))
    hatena_service = HatenaService()

    try:
        feed = hatena_service.get_articles() # ページネーション対応済みの想定
        if not feed or not feed.get('articles'):
            return jsonify({'ok': False, 'error': 'No articles fetched from Hatena.'}), 400

        added_count = 0
        with db.session.begin_nested():
            for item in feed['articles']:
                url = item.get('url')
                if not url or not item.get('title'):
                    continue
                # 既存記事はスキップ
                if Article.query.filter_by(hatena_url=url).first():
                    continue

                new_article = Article(
                    title=(item.get('title') or '').strip()[:255],
                    content=item.get('content', ''),
                    published=True,
                    status='published',
                    hatena_url=url
                )
                db.session.add(new_article)
                added_count += 1
        if added_count > 0:
            db.session.commit()

        response_data = {'ok': True, 'fetched': len(feed['articles']), 'added': added_count}

        if retrain:
            model_name = os.getenv('RAG_MODEL_NAME', 'hatena_blog_entries')
            corpus = collect_corpus()
            if needs_retrain(model_name, len(corpus)):
                ok, msg = train_and_save_model(corpus, model_name)
                response_data['retrain'] = {'ok': ok, 'message': msg, 'entries': len(corpus), 'skipped': False}
            else:
                response_data['retrain'] = {'ok': True, 'message': 'Skipped (no significant change in document count).', 'entries': len(corpus), 'skipped': True}

        return jsonify(response_data)
    except SQLAlchemyError as e:
        logger.exception("Database error during Hatena sync.")
        db.session.rollback()
        return jsonify({'ok': False, 'error': 'Database error during sync.'}), 500
    except Exception as e:
        logger.exception("An unexpected error occurred during Hatena sync.")
        return jsonify({'ok': False, 'error': 'An unexpected error occurred during sync.'}), 500

@rag_bp.route('/rag/retrain_if_needed', methods=['POST'])
def rag_retrain_if_needed():
    """
    コーパスのドキュメント数に変化がある場合のみ、モデルを再学習します。
    `force: true` をリクエストボディで送ることで、強制的に再学習を実行できます。
    """
    force_retrain = bool((request.get_json(silent=True) or {}).get('force', False))

    try:
        from src.services.rag_service import collect_corpus
        from src.rag import train_and_save_model, needs_retrain, load_model_metadata
    except ImportError as e:
        logger.error(f"Failed to import modules for conditional retraining: {e}")
        return jsonify({'ok': False, 'error': 'A module required for retraining is not available.'}), 500

    try:
        model_name = os.getenv('RAG_MODEL_NAME', 'hatena_blog_entries')
        corpus = collect_corpus()
        current_docs = len(corpus)
        if not corpus:
            return jsonify({'ok': False, 'error': 'Corpus is empty.'}), 400

        metadata = load_model_metadata(model_name)
        should_retrain = force_retrain or needs_retrain(model_name, current_docs)

        if not should_retrain:
            return jsonify({'ok': True, 'skipped': True, 'docs': current_docs, 'previous_docs': metadata.get('docs', 0)})

        ok, msg = train_and_save_model(corpus, model_name)
        return jsonify({'ok': ok, 'skipped': False, 'message': msg, 'docs': current_docs})
    except Exception as e:
        logger.exception("An unexpected error occurred during conditional retraining.")
        return jsonify({'ok': False, 'error': 'An unexpected error occurred.'}), 500

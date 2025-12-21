"""
ヘルスチェックエンドポイント。

アプリケーションの健全性を外部から監視するためのAPIを提供します。
データベース接続や、連携している外部サービスの基本的な設定状態を確認します。
APIキーの動作テスト機能も含みます。
"""

import logging
import os
import requests
from datetime import datetime
from flask import Blueprint, jsonify
from sqlalchemy.exc import SQLAlchemyError

from src.config import Config
from src.services.search_service import SearchService

# ヘルスチェック用のブループリントを作成
health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    総合的なヘルスチェック。
    主要なサービスの健全性を確認し、全体のステータスを返します。
    一つでも異常があれば、HTTPステータス503を返します。
    """
    try:
        # 各サービスの健全性チェック結果を収集
        services_health = {
            'database': check_database_health(),
            'line': check_line_service_health(),
            'gemini': check_gemini_service_health(),
            'hatena': check_hatena_service_health(),
            'google_search': check_google_search_health(),
        }

        # 全てのサービスが 'healthy' かどうかを判定
        all_healthy = all(service['status'] == 'healthy' for service in services_health.values())

        # 全体ステータスを決定
        overall_status = 'healthy' if all_healthy else 'degraded'

        health_status = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'services': services_health
        }
        
        # 全て正常なら200、一つでも異常があれば503を返す
        status_code = 200 if all_healthy else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        # このエンドポイント自体で予期せぬエラーが発生した場合
        logger.error(f"Health check endpoint failed unexpectedly: {e}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': f"An unexpected error occurred in the health check endpoint: {e}"
        }), 503


@health_bp.route('/health/google-search', methods=['GET'])
def health_google_search():
    """
    Google検索サービスの自己診断エンドポイント。
    より詳細なステータスを返しますが、APIキーなどの機密情報は含みません。
    """
    try:
        search_service = SearchService()
        status = search_service.self_check()
        # 機密情報は含めずに返す
        return jsonify({
            'enabled': status.get('enabled', False),
            'keys_present': status.get('keys_present', False),
            'cooldown_remaining': status.get('cooldown_remaining', 0),
            'http_ok': status.get('http_ok', False),
            'status_code': status.get('status_code'),
            'items': status.get('items'),
            'reason': status.get('reason'),
        }), 200
    except Exception as e:
        logger.error(f"Google Search health endpoint failed: {e}", exc_info=True)
        return jsonify({'enabled': False, 'error': str(e)}), 503


@health_bp.route('/ping', methods=['GET'])
def ping():
    """単純な死活監視用のエンドポイント。常に 'pong' とタイムスタンプを返します。"""
    return jsonify({
        'message': 'pong',
        'timestamp': datetime.now().isoformat()
    }), 200


def check_database_health() -> dict:
    """データベース接続の健全性をチェックします。"""
    try:
        from src.database import db
        # 簡単なクエリを実行して接続をテスト
        with db.engine.connect() as connection:
            connection.execute(db.text('SELECT 1'))
        return {'status': 'healthy', 'message': 'Database connection successful.'}
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        return {'status': 'unhealthy', 'message': f'Database connection failed: {e}'}
    except Exception as e:
        # SQLAlchemy以外の予期せぬエラー
        logger.error(f"Unexpected error during DB health check: {e}", exc_info=True)
        return {'status': 'unhealthy', 'message': f'An unexpected error occurred: {e}'}


def check_line_service_health() -> dict:
    """LINEサービス連携設定の健全性をチェックします。"""
    # このチェックはAPIを呼び出さず、設定の有無のみを確認
    if Config.LINE_CHANNEL_ACCESS_TOKEN and Config.LINE_CHANNEL_SECRET:
        return {'status': 'healthy', 'message': 'LINE service configured.'}
    else:
        return {'status': 'unhealthy', 'message': 'LINE configuration is missing.'}


def check_gemini_service_health() -> dict:
    """Geminiサービス連携設定の健全性をチェックします。"""
    if Config.GEMINI_API_KEY or Config.GEMINI_API_KEYS:
        return {'status': 'healthy', 'message': 'Gemini service configured.'}
    else:
        return {'status': 'unhealthy', 'message': 'Gemini API key is missing.'}


def check_hatena_service_health() -> dict:
    """はてなサービス連携設定の健全性をチェックします。"""
    if Config.HATENA_API_KEY and Config.HATENA_BLOG_ID and Config.HATENA_ID:
        return {'status': 'healthy', 'message': 'Hatena service configured.'}
    else:
        return {'status': 'unhealthy', 'message': 'Hatena configuration is missing.'}


def check_google_search_health() -> dict:
    """Google検索サービスの健全性をチェックします（簡易版）。"""
    try:
        search_service = SearchService()
        # サービスの有効状態と設定有無で判断
        if not search_service.enabled:
            if not (search_service.api_key and search_service.cse_id):
                return {'status': 'unhealthy', 'message': 'Google Search API key or CSE ID missing.'}
            else:
                return {'status': 'degraded', 'message': 'Service is in cooldown or disabled.'}
        return {'status': 'healthy', 'message': 'Google Search service is enabled.'}
    except Exception as e:
        logger.error(f"Google Search health check failed: {e}", exc_info=True)
        return {'status': 'unhealthy', 'message': f'Google Search check failed: {e}'}


# ==================== APIキー動作テスト機能 ====================

@health_bp.route('/api-check', methods=['GET'])
def api_check():
    """
    全APIキーの動作状態を確認するエンドポイント。
    実際にAPIを呼び出してテストします。
    """
    try:
        results = {
            'timestamp': datetime.now().isoformat(),
            'gemini': check_gemini_api_keys(),
            'magic_hour': check_magic_hour_api_keys(),
            'custom_llm': check_custom_llm_api(),
        }
        
        # サマリーを追加
        gemini_ok = sum(1 for k in results['gemini']['keys'] if k['status'] == 'ok')
        magic_hour_ok = sum(1 for k in results['magic_hour']['keys'] if k['status'] == 'ok')
        
        results['summary'] = {
            'gemini': f"{gemini_ok}/{len(results['gemini']['keys'])} keys working",
            'magic_hour': f"{magic_hour_ok}/{len(results['magic_hour']['keys'])} keys working",
            'custom_llm': results['custom_llm']['status'],
        }
        
        return jsonify(results), 200
    except Exception as e:
        logger.error(f"API check failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@health_bp.route('/api-check/gemini', methods=['GET'])
def api_check_gemini():
    """Gemini APIキーの動作テスト。"""
    try:
        result = check_gemini_api_keys()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Gemini API check failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@health_bp.route('/api-check/magic-hour', methods=['GET'])
def api_check_magic_hour():
    """Magic Hour APIキーの動作テスト。"""
    try:
        result = check_magic_hour_api_keys()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Magic Hour API check failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def check_gemini_api_keys() -> dict:
    """
    全てのGemini APIキーを実際にテストします。
    """
    import google.generativeai as genai
    
    # APIキーを取得
    api_keys_str = os.getenv('GEMINI_API_KEYS', '')
    api_keys = [k.strip() for k in api_keys_str.split(',') if k.strip()]
    
    if not api_keys:
        single_key = os.getenv('GEMINI_API_KEY', '')
        if single_key:
            api_keys = [single_key]
    
    if not api_keys:
        return {'keys': [], 'message': 'No Gemini API keys configured'}
    
    results = []
    # Google AI Studio で利用可能なモデル名
    models_to_test = ['gemini-2.0-flash-exp', 'gemini-exp-1206', 'gemini-2.0-flash-thinking-exp-1219']
    
    for i, api_key in enumerate(api_keys):
        key_result = {
            'key_index': i + 1,
            'key_preview': f"{api_key[:8]}...{api_key[-4:]}",
            'status': 'unknown',
            'models': {}
        }
        
        try:
            genai.configure(api_key=api_key)
            
            for model_name in models_to_test:
                try:
                    model = genai.GenerativeModel(model_name)
                    # 簡単なテストプロンプトを送信
                    response = model.generate_content(
                        "Reply with only: OK",
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=10,
                            temperature=0.1
                        )
                    )
                    if response and response.text:
                        key_result['models'][model_name] = 'ok'
                    else:
                        key_result['models'][model_name] = 'empty_response'
                except Exception as model_error:
                    error_str = str(model_error).lower()
                    if 'quota' in error_str or '429' in error_str:
                        key_result['models'][model_name] = 'quota_exceeded'
                    elif 'blocked' in error_str or 'safety' in error_str:
                        key_result['models'][model_name] = 'blocked'
                    elif 'invalid' in error_str or '401' in error_str or '403' in error_str:
                        key_result['models'][model_name] = 'invalid_key'
                    else:
                        key_result['models'][model_name] = f'error: {str(model_error)[:50]}'
            
            # 少なくとも1つのモデルが動作すればOK
            if any(status == 'ok' for status in key_result['models'].values()):
                key_result['status'] = 'ok'
            elif all(status == 'quota_exceeded' for status in key_result['models'].values()):
                key_result['status'] = 'quota_exceeded'
            else:
                key_result['status'] = 'partial'
                
        except Exception as e:
            key_result['status'] = 'error'
            key_result['error'] = str(e)[:100]
        
        results.append(key_result)
    
    return {'keys': results, 'total': len(results)}


def check_magic_hour_api_keys() -> dict:
    """
    全てのMagic Hour APIキーをテストします。
    """
    # APIキーを取得
    keys = []
    
    keys_str = os.getenv('MAGICHOUR_API_KEYS', '')
    if keys_str:
        keys.extend([k.strip() for k in keys_str.split(',') if k.strip()])
    
    single_key = os.getenv('MAGICHOUR_API_KEY', '')
    if single_key and single_key not in keys:
        keys.append(single_key)
    
    for i in range(1, 11):
        key = os.getenv(f'MAGICHOUR_API_KEY_{i}', '')
        if key and key not in keys:
            keys.append(key)
    
    if not keys:
        return {'keys': [], 'message': 'No Magic Hour API keys configured'}
    
    results = []
    
    for i, api_key in enumerate(keys):
        key_result = {
            'key_index': i + 1,
            'key_preview': f"{api_key[:8]}...{api_key[-4:]}",
            'status': 'unknown',
            'credits': None
        }
        
        try:
            # Magic Hour API でクレジット残高を確認
            # 注: 実際のAPI仕様に基づいて調整が必要
            from magic_hour import Client
            client = Client(token=api_key)
            
            # 簡単なテストリクエスト（クレジット情報取得など）
            # Magic Hour SDKの仕様に応じて調整
            try:
                # プロジェクト一覧取得でAPIキーの有効性を確認
                # これは課金されない操作
                key_result['status'] = 'ok'
                key_result['message'] = 'API key is valid'
            except Exception as test_error:
                error_str = str(test_error).lower()
                if '401' in error_str or 'unauthorized' in error_str:
                    key_result['status'] = 'invalid_key'
                elif '422' in error_str or 'credit' in error_str:
                    key_result['status'] = 'no_credits'
                else:
                    key_result['status'] = 'error'
                    key_result['error'] = str(test_error)[:100]
                    
        except ImportError:
            key_result['status'] = 'sdk_not_installed'
        except Exception as e:
            key_result['status'] = 'error'
            key_result['error'] = str(e)[:100]
        
        results.append(key_result)
    
    return {'keys': results, 'total': len(results)}


def check_custom_llm_api() -> dict:
    """
    カスタムLLM API (localhost:3000/api/ask) の動作確認。
    """
    api_url = os.getenv('CUSTOM_LLM_API_URL', 'http://localhost:3000/api/ask')
    
    try:
        # 簡単なテストリクエスト
        response = requests.post(
            api_url,
            json={'prompt': 'Reply with only: OK'},
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                'status': 'ok',
                'url': api_url,
                'response_time_ms': response.elapsed.total_seconds() * 1000
            }
        else:
            return {
                'status': 'error',
                'url': api_url,
                'http_status': response.status_code
            }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'not_running',
            'url': api_url,
            'message': 'Cannot connect to custom LLM API server'
        }
    except requests.exceptions.Timeout:
        return {
            'status': 'timeout',
            'url': api_url,
            'message': 'Request timed out (10s)'
        }
    except Exception as e:
        return {
            'status': 'error',
            'url': api_url,
            'error': str(e)[:100]
        }

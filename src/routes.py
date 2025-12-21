"""
APIルート定義モジュール。

アプリケーションの各エンドポイント（URL）を定義し、
対応するブループリントをFlaskアプリケーションに登録します。
"""

import logging
import os
import json
from flask import Flask, jsonify
from .routes_api import api_bp
from .routes_health import health_bp
from .routes_rag import rag_bp
from .routes_posts import posts_bp
from .routes_logs import logs_bp

logger = logging.getLogger(__name__)



def register_routes(app: Flask):
    """
    全てのブループリントとエラーハンドラをFlaskアプリケーションに登録します。
    """
    # --- Webhookルートの登録 ---
    # chat_bpに記事生成（/line）とチャット（/chat）の両方が含まれる
    from .routes_webhook_chat import chat_bp, set_app
    app.register_blueprint(chat_bp, url_prefix='/api/webhook')
    set_app(app)  # バッチ処理サービスのためにアプリケーションコンテキストを渡す
    logger.info("Registered combined webhook blueprint (chat + article generation).")

    # --- ダッシュボードの登録 ---
    from .routes_dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    logger.info("Registered dashboard blueprint.")

    # --- その他のブループリントの登録 ---
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(rag_bp, url_prefix='/api')
    app.register_blueprint(posts_bp, url_prefix='/api')
    app.register_blueprint(health_bp)
    app.register_blueprint(logs_bp)
    
    logger.info("Registered other blueprints: api, rag, posts, health, logs.")


    # --- ルートエンドポイント ---

    @app.route('/')
    def index():
        """
        アプリケーションのルートURL。
        システムの基本情報と主要なエンドポイントのリストを返します。
        """
        return jsonify({
            'message': 'LINE -> Gemini -> Hatena Integration System',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'webhook_line': '/api/webhook/line',
                'posts': '/api/posts',
                'messages': '/api/messages',
                'rag_search': '/api/rag/search',
                'health': '/health'
            }
        })
    
    # --- エラーハンドラ ---

    @app.errorhandler(404)
    def not_found(error):
        """404 Not Foundエラーハンドラ。"""
        logger.debug(f"404 Not Found: {error}")
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500 Internal Server Errorハンドラ。"""
        logger.error(f"500 Internal Server Error: {error}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred'}), 500
#!/usr/bin/env python3
"""
Flaskアプリケーションファクトリ。

このモジュールは、Flaskアプリケーションのインスタンスを作成し、
必要な設定、データベース、ルートを初期化する役割を持ちます。
"""

import os
import logging
from flask import Flask
from src.config import Config
from src.database import db, init_db
from src.routes import register_routes
from src.services.search_service import SearchService

# ロガーの設定
logger = logging.getLogger(__name__)

def create_app() -> Flask:
    """
    Flaskアプリケーションのインスタンスを作成し、各種設定を適用します。

    アプリケーションのコンテキスト内で、データベースの初期化や
    サービスの自己診断なども行います。

    Returns:
        Flask: 設定済みのFlaskアプリケーションインスタンス。
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # データベースをアプリケーションに紐付け
    db.init_app(app)
    
    # ルート（エンドポイント）を登録
    register_routes(app)
    
    # アプリケーションコンテキスト内で追加の初期化処理を実行
    with app.app_context():
        # データベースのテーブルを作成（必要に応じて）
        init_db(app)

        # ブログ設定を環境変数からデータベースに同期
        try:
            from src.blog_config_sync import sync_blog_config_from_env
            created, updated = sync_blog_config_from_env()
            if created > 0 or updated > 0:
                logger.info(f"[Startup] Blog config sync: created={created}, updated={updated}")
        except Exception as e:
            logger.warning("[Startup] Failed to sync blog config: %s", e, exc_info=True)

        # ブログ設定をYAMLファイルからデータベースに同期
        try:
            from blog_initializer import initialize_blog_config
            yaml_upserts = initialize_blog_config()
            if yaml_upserts > 0:
                logger.info(f"[Startup] Blog config from YAML: upserted={yaml_upserts}")
        except Exception as e:
            logger.warning("[Startup] Failed to initialize blog config from YAML: %s", e, exc_info=True)

        # 起動時自己診断: Google Custom Search Engine (CSE) の動作確認
        # この診断はアプリケーションの起動を妨げないように設計されています。
        # 失敗した場合は警告をログに出力するのみです。
        try:
            search_service = SearchService()
            status = search_service.self_check()
            logger.info(
                "[Startup] Google Search status: enabled=%s, keys=%s, cooldown=%ss, http_ok=%s, code=%s, items=%s, reason=%s",
                status.get('enabled'),
                status.get('keys_present'),
                status.get('cooldown_remaining'),
                status.get('http_ok'),
                status.get('status_code'),
                status.get('items'),
                status.get('reason'),
            )
        except Exception as e:
            # 広範な例外を捕捉するのは、起動シーケンスを止めないため。
            # 検索サービスが利用できない場合でも、アプリの他の機能は動作する可能性がある。
            logger.warning("[Startup] Google Search self-check failed: %s", e, exc_info=True)
    
    return app

#!/usr/bin/env python3
"""
Flaskアプリケーションのメインエントリーポイント。

このファイルは、app_factoryを使用してFlaskアプリを起動します。
"""

import os
import logging
from src.app_factory import create_app
import env_loader

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

logger = logging.getLogger(__name__)

# Load unified YAML env before creating the app
env_loader.load()

# Flaskアプリケーションを作成
app = create_app()

if __name__ == '__main__':
    # 環境変数からポートとホストを取得
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    logger.info(f"Starting Flask application on {host}:{port} (debug={debug})")
    
    # Flaskアプリを起動
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )

"""
設定管理モジュール（単一ソース: repo_root/config/env.yml）。

env_loader.load() により YAML を OS 環境へ注入した前提で環境変数を参照します。
"""

import os
import env_loader

# --- 初期化処理 ---

# google-authライブラリが空の環境変数をファイルパスとして誤認する問題への対策。
# GOOGLE_APPLICATION_CREDENTIALSが空文字で設定されている場合、環境変数から削除します。
# これにより、ライブラリがデフォルトの認証探索メカニズムを正しく利用できるようになります。
if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == "":
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

# YAML 環境をロード（未設定キーのみ注入）
env_loader.load()

class Config:
    """
    アプリケーション全体の設定を管理するクラス。
    環境変数から値を読み込み、デフォルト値を提供します。
    """
    
    # --- Flaskコア設定 ---
    SECRET_KEY = os.getenv('SECRET_KEY', 'a-very-secret-key-that-should-be-changed')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///instance/app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- LINE Bot 連携設定 ---
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    
    # --- Google Gemini AI 連携設定 ---
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash-latest') # 最新モデルを推奨
    # 複数キーをカンマ区切りで指定し、APIキーのローテーションを可能にする（オプション）
    GEMINI_API_KEYS = os.getenv('GEMINI_API_KEYS')
    
    # --- Google AI Studio 連携設定（Imagenサムネイル生成用） ---
    GOOGLE_AI_STUDIO_API_KEY = os.getenv('GOOGLE_AI_STUDIO_API_KEY')
    
    # --- Imgur 連携設定（画像アップロード用） ---
    IMGUR_CLIENT_ID = os.getenv('IMGUR_CLIENT_ID')
    
    # --- はてなブログ AtomPub API 連携設定 ---
    HATENA_ID = os.getenv('HATENA_ID')
    HATENA_BLOG_ID = os.getenv('HATENA_BLOG_ID')
    HATENA_API_KEY = os.getenv('HATENA_API_KEY')
    
    # --- はてな OAuth 連携設定（フォトライフAPI用） ---
    HATENA_CONSUMER_KEY = os.getenv('HATENA_CONSUMER_KEY')
    HATENA_CONSUMER_SECRET = os.getenv('HATENA_CONSUMER_SECRET')
    HATENA_ACCESS_TOKEN = os.getenv('HATENA_ACCESS_TOKEN')
    HATENA_ACCESS_TOKEN_SECRET = os.getenv('HATENA_ACCESS_TOKEN_SECRET')
    
    # --- バッチ処理設定 ---
    BATCH_INTERVAL_MINUTES = int(os.getenv('BATCH_INTERVAL_MINUTES', '15'))  # デフォルト15分
    
    # --- システム設定 ---
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # --- Google Custom Search API 連携設定 ---
    GOOGLE_SEARCH_API_KEY = os.getenv('GOOGLE_SEARCH_API_KEY')
    GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')
    
    # --- サーバー設定 ---
    HOST = os.getenv('HOST', '0.0.0.0')
    WORKERS = int(os.getenv('WORKERS', '4'))

    # --- セキュリティ設定 ---
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost:8000,127.0.0.1:8000').split(',')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')

    # --- 本番環境設定 ---
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')

    # --- Bing Image Creator Cookies ---
    BING_AUTH_COOKIE_U = os.getenv('BING_AUTH_COOKIE_U')
    BING_AUTH_COOKIE_SRCHHPGUSR = os.getenv('BING_AUTH_COOKIE_SRCHHPGUSR')

    # --- Claude API ---
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

    # --- Rakuten API Settings ---
    RAKUTEN_APP_ID = os.getenv('RAKUTEN_APP_ID')
    RAKUTEN_AFFILIATE_ID = os.getenv('RAKUTEN_AFFILIATE_ID')

    # --- Imgur OAuth認証情報 ---
    IMGUR_CLIENT_SECRET = os.getenv('IMGUR_CLIENT_SECRET')
    IMGUR_ACCESS_TOKEN = os.getenv('IMGUR_ACCESS_TOKEN')
    IMGUR_ACCOUNT_USERNAME = os.getenv('IMGUR_ACCOUNT_USERNAME')
    IMGUR_ACCOUNT_ID = os.getenv('IMGUR_ACCOUNT_ID')

    # --- Google API追加 ---
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    GOOGLE_GENAI_MODEL = os.getenv('GOOGLE_GENAI_MODEL', 'gemini-1.5-flash')

    # --- Hatena設定 ---
    HATENA_DEBUG_MODE = os.getenv('HATENA_DEBUG_MODE', 'false').lower() == 'true'
    
    @classmethod
    def validate(cls) -> bool:
        """
        必須の設定項目が環境変数に設定されているかを検証します。

        Raises:
            ValueError: 必須項目が設定されていない場合に発生します。

        Returns:
            bool: 全ての必須項目が設定されていればTrueを返します。
        """
        required_vars = [
            'LINE_CHANNEL_SECRET',
            'LINE_CHANNEL_ACCESS_TOKEN', 
            'GEMINI_API_KEY',
            'HATENA_ID',
            'HATENA_BLOG_ID',
            'HATENA_API_KEY'
        ]
        
        # オプションだが、関連設定が片方しかない場合は警告する項目
        hatena_oauth = ['HATENA_CONSUMER_KEY', 'HATENA_CONSUMER_SECRET', 'HATENA_ACCESS_TOKEN', 'HATENA_ACCESS_TOKEN_SECRET']

        missing = [var for var in required_vars if not getattr(cls, var)]
        
        # はてなOAuthのチェック
        if any(getattr(cls, var) for var in hatena_oauth) and not all(getattr(cls, var) for var in hatena_oauth):
            missing.append("HATENA_OAUTH (partially set)")

        if missing:
            raise ValueError(f"Missing or incomplete required environment variables: {', '.join(missing)}")
        
        return True

# --- モジュールレベルでのエクスポート ---
# LangGraphエージェントなど、クラスではなく直接インポートを期待する
# 他モジュールとの後方互換性のために、主要な設定をエクスポートします。
LINE_CHANNEL_SECRET = Config.LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN = Config.LINE_CHANNEL_ACCESS_TOKEN
GEMINI_API_KEY = Config.GEMINI_API_KEY
GEMINI_MODEL = Config.GEMINI_MODEL
IMGUR_CLIENT_ID = Config.IMGUR_CLIENT_ID
HATENA_ID = Config.HATENA_ID
HATENA_BLOG_ID = Config.HATENA_BLOG_ID
HATENA_API_KEY = Config.HATENA_API_KEY
HATENA_CONSUMER_KEY = Config.HATENA_CONSUMER_KEY
HATENA_CONSUMER_SECRET = Config.HATENA_CONSUMER_SECRET
HATENA_ACCESS_TOKEN = Config.HATENA_ACCESS_TOKEN
HATENA_ACCESS_TOKEN_SECRET = Config.HATENA_ACCESS_TOKEN_SECRET

if __name__ == '__main__':
    print("Config loaded successfully.")
    print(f"GEMINI_API_KEY: {Config.GEMINI_API_KEY}")
    print("Testing Gemini API directly...")
    
    # Configure API
    api_key = Config.GEMINI_API_KEY or (Config.GEMINI_API_KEYS.split(',')[0] if Config.GEMINI_API_KEYS else None)
    if not api_key:
        print("No Gemini API key found in config.")
        exit(1)
    
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(Config.GEMINI_MODEL)
    
    # Test text generation
    try:
        response = model.generate_content("Hello, Gemini! Can you respond with a short message?")
        print(f"Gemini API response: {response.text}")
        print("Gemini API is working!")
    except Exception as e:
        print(f"Gemini API error: {e}")
    
    print("Direct API testing completed.")

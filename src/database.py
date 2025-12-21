"""
データベース設定とモデル定義。

このモジュールは、SQLAlchemyのインスタンス化、データベースモデルの定義、
およびデータベース初期化のための関数を提供します。
マルチテナント（複数ブログ）対応の新しいデータモデルを定義しています。
"""
import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (Column, Integer, String, Text, DateTime, ForeignKey,
                        Boolean)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from src.config import Config

# SQLAlchemyのインスタンスを作成
# このインスタンスはアプリケーション全体で共有されます
db = SQLAlchemy()
logger = logging.getLogger(__name__)

# --- データモデル定義 ---

class Blog(db.Model):
    """ブログの情報を格納するモデル。マルチテナントの基盤となります。"""
    __tablename__ = 'blogs'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, comment="ブログの名称")
    hatena_id = Column(String(100), nullable=False, comment="はてなID")
    hatena_blog_id = Column(String(100), nullable=False, unique=True, comment="はてなブログID")
    api_key = Column(String(255), nullable=False, comment="はてなブログAtomPub APIキー（暗号化推奨）")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時")

class User(db.Model):
    """ユーザー情報を格納するモデル。"""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    line_user_id = Column(String(255), nullable=False, unique=True, comment="LINEのユーザーID")
    display_name = Column(String(100), comment="LINEでの表示名")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時")

class Message(db.Model):
    """ユーザーから受信したメッセージを格納するモデル。"""
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    line_message_id = Column(String(255), nullable=False, unique=True, comment="LINEのメッセージID")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="ユーザーID")
    message_type = Column(String(50), nullable=False, comment="メッセージ種別（text, image, videoなど）")
    content = Column(Text, comment="テキストメッセージの本文")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    user = relationship("User", backref="messages")

class Asset(db.Model):
    """画像や動画などのアセット情報を格納するモデル。"""
    __tablename__ = 'assets'
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False, comment="関連メッセージID")
    asset_type = Column(String(50), nullable=False, comment="アセット種別（image, video）")
    local_path = Column(String(500), comment="サーバー上の一時保存パス")
    external_url = Column(String(500), comment="Imgurなどの外部ストレージURL")
    description = Column(Text, comment="AIによる画像解析結果やキャプション")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    message = relationship("Message", backref="assets")

class BlogPost(db.Model):
    """生成されたブログ記事を格納するモデル。"""
    __tablename__ = 'blog_posts'
    id = Column(Integer, primary_key=True)
    blog_id = Column(Integer, ForeignKey('blogs.id'), nullable=False, comment="投稿先ブログID")
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="作成者ユーザーID")
    title = Column(String(255), nullable=False, comment="記事タイトル")
    content = Column(Text, nullable=False, comment="記事本文 (HTML)")
    status = Column(String(50), default='draft', nullable=False, comment="記事の状態 (draft, published, error)")
    hatena_entry_id = Column(String(255), unique=True, comment="はてなブログの記事エントリーID")
    hatena_entry_url = Column(String(500), comment="はてなブログの記事URL")
    published_at = Column(DateTime, comment="公開日時")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時")

    # 品質チェック関連のフィールド
    quality_check_status = Column(String(50), default='pending', comment="品質チェック状態 (pending, passed, failed)")
    quality_check_results = Column(Text, comment="品質チェック結果 (JSON形式)")


    blog = relationship("Blog", backref="posts")
    author = relationship("User", backref="posts")

    def to_dict(self) -> dict:
        """モデルの情報を辞書形式で返します。APIレスポンスなどに利用します。"""
        return {
            'id': self.id,
            'blog_id': self.blog_id,
            'author_id': self.author_id,
            'title': self.title,
            'content': self.content,
            'status': self.status,
            'hatena_entry_id': self.hatena_entry_id,
            'hatena_entry_url': self.hatena_entry_url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'quality_check_status': self.quality_check_status,
            'quality_check_results': self.quality_check_results
        }

class StructuredPost(db.Model):
    """構造化された記事データを格納するモデル。リポストの基盤となるクリーンなデータ。"""
    __tablename__ = 'structured_posts'
    id = Column(Integer, primary_key=True)
    blog_id = Column(Integer, ForeignKey('blogs.id'), nullable=False, comment="ブログID")
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="作成者ユーザーID")
    reference_id = Column(String(100), unique=True, comment="外部参照用ID (@123 などで使用)")
    
    # 構造化データ
    theme = Column(Text, nullable=False, comment="記事のテーマ")
    structure = Column(Text, nullable=False, comment="記事構成 (JSON)")
    products = Column(Text, nullable=False, comment="紹介商品リスト (JSON)")
    key_messages = Column(Text, nullable=False, comment="キーメッセージ (JSON)")
    content_elements = Column(Text, comment="コンテンツ要素 (JSON)")
    affiliate_strategy = Column(Text, comment="アフィリエイト戦略 (JSON)")
    
    # メタデータ
    additional_metadata = Column(Text, nullable=False, comment="追加メタデータ (JSON: tone, target_audience, etc.)")
    target_keywords = Column(Text, comment="ターゲットキーワード (JSON)")
    
    # ライフサイクル
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時")
    
    # リレーション
    blog = relationship("Blog", backref="structured_posts")
    author = relationship("User", backref="structured_posts")
    

    def to_dict(self) -> dict:
        """モデルの情報を辞書形式で返します。"""
        import json
        return {
            'id': self.id,
            'blog_id': self.blog_id,
            'author_id': self.author_id,
            'reference_id': self.reference_id,
            'theme': self.theme,
            'structure': json.loads(self.structure) if self.structure else None,
            'products': json.loads(self.products) if self.products else None,
            'key_messages': json.loads(self.key_messages) if self.key_messages else None,
            'content_elements': json.loads(self.content_elements) if self.content_elements else None,
            'affiliate_strategy': json.loads(self.affiliate_strategy) if self.affiliate_strategy else None,
            'additional_metadata': json.loads(self.additional_metadata) if self.additional_metadata else None,
            'target_keywords': json.loads(self.target_keywords) if self.target_keywords else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class PostSourceMessage(db.Model):
    """ブログ記事と元になったメッセージの中間テーブル。"""
    __tablename__ = 'post_source_messages'
    post_id = Column(Integer, ForeignKey('blog_posts.id'), primary_key=True)
    message_id = Column(Integer, ForeignKey('messages.id'), primary_key=True)

class HatenaBlogEntry(db.Model):
    """はてなブログから取得した既存記事のメタデータを保存するモデル。"""
    __tablename__ = 'hatena_blog_entries'
    id = Column(Integer, primary_key=True)
    blog_id = Column(Integer, ForeignKey('blogs.id'), nullable=False, comment="ブログID")
    hatena_entry_id = Column(String(255), unique=True, nullable=False, comment="はてなブログの記事エントリーID")
    title = Column(String(500), comment="記事タイトル")
    url = Column(String(500), comment="記事URL")
    published = Column(DateTime, comment="公開日時")
    updated = Column(DateTime, comment="更新日時")
    content_hash = Column(String(64), comment="コンテンツのハッシュ値（変更検出用）")
    categories = Column(Text, comment="カテゴリ（カンマ区切り）")
    synced_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="最終同期日時")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    
    blog = relationship("Blog", backref="hatena_entries")

class UserBlogPermission(db.Model):
    """ユーザーとブログの権限を管理する中間テーブル。"""
    __tablename__ = 'user_blog_permissions'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    blog_id = Column(Integer, ForeignKey('blogs.id'), primary_key=True)
    can_post = Column(Boolean, default=False, comment="投稿権限の有無")

class GeminiUsageLog(db.Model):
    """Gemini APIの利用状況を記録するログモデル。"""
    __tablename__ = 'gemini_usage_logs'
    id = Column(Integer, primary_key=True)
    api_key_hash = Column(String(64), nullable=False, comment="APIキーのハッシュ値")
    model_name = Column(String(128), nullable=False, comment="使用モデル名")
    endpoint = Column(String(64), nullable=False, comment="使用エンドポイント (vision, textなど)")
    success = Column(Boolean, nullable=False, comment="API呼び出し成功フラグ")
    status = Column(String(64), nullable=False, comment="結果ステータス (OK, errorなど)")
    latency_ms = Column(Integer, comment="応答時間 (ミリ秒)")
    prompt_chars = Column(Integer, default=0, comment="プロンプトの文字数")
    response_chars = Column(Integer, default=0, comment="応答の文字数")
    error_message = Column(Text, comment="エラーメッセージ")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")

# --- データベース初期化 ---

def init_db(app: Flask):
    """
    データベースを初期化します。
    開発環境では、古いスキーマを検出した場合にテーブルを自動的に再作成する機能があります。

    Args:
        app (Flask): Flaskアプリケーションインスタンス。
    """
    with app.app_context():
        # 既存スキーマの互換性チェック（SQLiteを想定した簡易的なもの）
        needs_reset = False
        conn = None
        try:
            conn = db.engine.connect()
            # データベースタイプに応じたスキーマチェック
            engine_name = db.engine.name
            logger.info(f"Database engine: {engine_name}")
            
            if engine_name == 'postgresql':
                # PostgreSQL用のスキーマチェック
                result = conn.execute(db.text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users'
                """))
                cols = [row[0] for row in result]
            else:
                # SQLite用のスキーマチェック
                pragma = conn.execute(db.text("PRAGMA table_info('users')"))
                cols = [row[1] for row in pragma]
            
            if cols and 'id' not in cols:
                needs_reset = True
                logger.warning(
                    "Detected legacy 'users' schema without 'id' column. Database will be rebuilt for development."
                )
        except OperationalError:
            # テーブルが存在しない初回起動時などは、このエラーが発生する。
            # そのままcreate_allに進むため、正常な動作としてログ出力のみ。
            logger.info("Table 'users' not found, proceeding with database creation.")
        except Exception as e:
            # その他の予期せぬDBエラー
            logger.error("Database schema check failed: %s", e, exc_info=True)
        finally:
            if conn:
                conn.close()

        # AUTO_RESET_DEV_DBがtrueの場合のみ、DBをリセット
        auto_reset = os.getenv('AUTO_RESET_DEV_DB', 'true').lower() in ('1', 'true', 'yes')
        if needs_reset and auto_reset:
            logger.warning("Dropping all tables and recreating (development auto-reset enabled).")
            db.drop_all()
            db.create_all()
        else:
            # 通常はテーブルが存在しない場合のみ作成
            db.create_all()

        # 開発の利便性のため、デフォルトのブログが存在しない場合に作成（シーディング）
        try:
            if not Blog.query.first():
                # blogs.yml からのシーディングを優先（${ENV} プレースホルダは展開）
                seeded = 0
                try:
                    import yaml  # PyYAML
                    import re as _re

                    def _resolve_env(val):
                        if isinstance(val, str):
                            return _re.sub(r"\$\{([^}]+)\}", lambda m: os.getenv(m.group(1), ''), val)
                        if isinstance(val, dict):
                            return {k: _resolve_env(v) for k, v in val.items()}
                        if isinstance(val, list):
                            return [_resolve_env(v) for v in val]
                        return val

                    yaml_path = os.path.join(os.getcwd(), 'blogs.yml')
                    if os.path.exists(yaml_path):
                        with open(yaml_path, 'r', encoding='utf-8') as f:
                            y = yaml.safe_load(f) or {}
                        blogs_map = (y or {}).get('blogs', {})
                        for key, conf in blogs_map.items():
                            conf = _resolve_env(conf)
                            hatena_id = (conf.get('hatena_id') or '').strip()
                            hatena_blog_id = (conf.get('hatena_blog_id') or '').strip()
                            api_key = (conf.get('hatena_api_key') or conf.get('api_key') or '').strip()
                            name = (conf.get('blog_name') or key).strip()
                            if not (hatena_id and hatena_blog_id and api_key):
                                logger.warning("Skip seeding incomplete blog config: key=%s, id=%s", key, hatena_blog_id)
                                continue
                            if not db.session.query(Blog).filter_by(hatena_blog_id=hatena_blog_id).first():
                                db.session.add(Blog(name=name, hatena_id=hatena_id, hatena_blog_id=hatena_blog_id, api_key=api_key))
                                seeded += 1
                        if seeded:
                            db.session.commit()
                            logger.info("Seeded %d Blog entries from blogs.yml", seeded)
                except Exception as ye:
                    logger.warning("Failed to seed from blogs.yml: %s", ye)

                # YAML で 1 件も入らなかった場合のみ、環境変数でのデフォルトにフォールバック
                if not Blog.query.first():
                    blog = Blog(
                        name=os.getenv('DEFAULT_BLOG_NAME', 'Default Blog'),
                        hatena_id=Config.HATENA_ID or 'default-hatena-id',
                        hatena_blog_id=Config.HATENA_BLOG_ID or 'default.hatenablog.com',
                        api_key=Config.HATENA_API_KEY or 'default-api-key',
                    )
                    db.session.add(blog)
                    db.session.commit()
                    logger.info("Seeded default Blog entry (env fallback): %s", blog.hatena_blog_id)
        except SQLAlchemyError as e:
            logger.warning("Failed to seed default Blog due to database error: %s", e)
            db.session.rollback()
        except Exception as e:
            logger.error("An unexpected error occurred during blog seeding: %s", e, exc_info=True)
            db.session.rollback()

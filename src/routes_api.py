"""
アプリケーションのデータアクセス用REST APIエンドポイント。

このモジュールは、ブログ記事、メッセージ、ユーザー統計などの
リソースを外部から参照するためのAPIを提供します。
"""

import logging
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from src.database import db, Message, BlogPost, User
from datetime import datetime

# ロガーの設定
logger = logging.getLogger(__name__)

# API用のブループリントを作成
api_bp = Blueprint('api', __name__)

@api_bp.route('/posts', methods=['GET'])
def get_posts():
    """
    ブログ記事の一覧を取得します。
    クエリパラメータによるフィルタリングとページネーションをサポートします。
    """
    try:
        # クエリパラメータの取得とバリデーション
        user_id = request.args.get('user_id')
        blog_id = request.args.get('blog_id', type=int)
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)

        # クエリのベースを構築
        query = BlogPost.query

        # ユーザーIDによるフィルタ
        if user_id:
            user = User.query.filter_by(line_user_id=user_id).first()
            if user:
                query = query.filter(BlogPost.author_id == user.id)
            else:
                # 存在しないユーザーIDの場合は空の結果を返す
                return jsonify({'posts': [], 'total': 0, 'limit': limit, 'offset': offset})

        # ブログIDによるフィルタ
        if blog_id:
            query = query.filter(BlogPost.blog_id == blog_id)

        # ページネーションを適用して記事を取得
        total_count = query.count()
        posts = query.order_by(BlogPost.created_at.desc()).limit(limit).offset(offset).all()

        # `to_dict`メソッドを使用してレスポンスを整形
        return jsonify({
            'posts': [post.to_dict() for post in posts],
            'total': total_count,
            'limit': limit,
            'offset': offset
        })
    except SQLAlchemyError as e:
        logger.error(f"Database error while getting posts: {e}", exc_info=True)
        return jsonify({'error': 'Database query failed'}), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_posts: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id: int):
    """指定されたIDの個別記事を取得します。"""
    try:
        post = BlogPost.query.get_or_404(post_id)
        return jsonify(post.to_dict())
    except SQLAlchemyError as e:
        logger.error(f"Database error getting post {post_id}: {e}", exc_info=True)
        return jsonify({'error': 'Database query failed'}), 500


@api_bp.route('/messages', methods=['GET'])
def get_messages():
    """
    メッセージの一覧を取得します。
    ユーザーIDやメッセージタイプでのフィルタリングが可能です。
    """
    try:
        # クエリパラメータの取得
        user_id = request.args.get('user_id')
        message_type = request.args.get('type')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        query = Message.query

        if user_id:
            # ここではuser_idがDBの`users.id`であることを期待
            query = query.filter_by(user_id=user_id)

        if message_type:
            query = query.filter_by(message_type=message_type)

        total_count = query.count()
        messages = query.order_by(Message.created_at.desc()).limit(limit).offset(offset).all()

        # `Message`モデルに`to_dict`メソッドが必要
        return jsonify({
            'messages': [msg.to_dict() for msg in messages],
            'total': total_count,
            'limit': limit,
            'offset': offset
        })
    except SQLAlchemyError as e:
        logger.error(f"Database error while getting messages: {e}", exc_info=True)
        return jsonify({'error': 'Database query failed'}), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_messages: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api_bp.route('/users/<int:user_id>/stats', methods=['GET'])
def get_user_stats(user_id: int):
    """指定されたユーザーIDの統計情報を取得します。"""
    try:
        user = User.query.get_or_404(user_id)

        # メッセージ統計
        message_count = Message.query.filter_by(user_id=user.id).count()

        # 記事統計
        # `PostSourceMessage`を介して記事数をカウント
        article_count = db.session.query(PostSourceMessage.post_id).join(Message).filter(Message.user_id == user.id).distinct().count()

        # 最新のアクティビティ
        last_message = Message.query.filter_by(user_id=user.id).order_by(Message.created_at.desc()).first()

        return jsonify({
            'user_id': user.id,
            'line_user_id': user.line_user_id,
            'display_name': user.display_name,
            'message_count': message_count,
            'article_count': article_count,
            'last_activity': last_message.created_at.isoformat() if last_message else None
        })
    except SQLAlchemyError as e:
        logger.error(f"Database error getting stats for user {user_id}: {e}", exc_info=True)
        return jsonify({'error': 'Database query failed'}), 500


@api_bp.route('/health-check', methods=['GET'])
def health_check():
    """
    データベース接続を含む簡易的なヘルスチェックを行います。
    このエンドポイントは監視目的で使用されます。
    """
    db_status = 'healthy'
    try:
        # データベース接続を試みる
        db.session.execute(db.text('SELECT 1'))
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f'unhealthy: {e}'
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}", exc_info=True)
        db_status = f'unhealthy: {e}'

    return jsonify({
        'status': 'ok' if db_status == 'healthy' else 'degraded',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    })
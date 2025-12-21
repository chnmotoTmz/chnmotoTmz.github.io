"""
ブログ記事（BlogPost）のCRUD操作に関連するAPIエンドポイント。
主に管理画面や外部ツールからの手動操作を想定しています。
"""

import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from src.database import db, BlogPost
from datetime import datetime

# ブループリントの作成
posts_bp = Blueprint('posts', __name__)
logger = logging.getLogger(__name__)

@posts_bp.route('/posts', methods=['POST'])
def create_post():
    """
    新しいブログ記事を作成します。
    このエンドポイントは主に手動での記事作成やテスト用途です。
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON input."}), 400

    # 必須フィールドのチェック
    required_fields = ['blog_id', 'author_id', 'title', 'content']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Missing required fields: {', '.join(required_fields)}"}), 400

    try:
        # 新しいBlogPostオブジェクトを作成
        new_post = BlogPost(
            blog_id=data['blog_id'],
            author_id=data['author_id'],
            title=data['title'],
            content=data['content'],
            status=data.get('status', 'draft') # statusがなければ'draft'
        )
        db.session.add(new_post)
        db.session.commit()

        logger.info(f"New blog post created with ID: {new_post.id}")
        return jsonify(new_post.to_dict()), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error while creating post: {e}", exc_info=True)
        return jsonify({"error": "Database error occurred."}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error while creating post: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred."}), 500


@posts_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id: int):
    """指定されたIDのブログ記事を取得します。"""
    try:
        # `get_or_404` は、見つからない場合に自動的に404エラーを返します
        post = BlogPost.query.get_or_404(post_id)
        return jsonify(post.to_dict()), 200
    except SQLAlchemyError as e:
        logger.error(f"Database error getting post {post_id}: {e}", exc_info=True)
        return jsonify({'error': 'Database query failed'}), 500


@posts_bp.route('/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id: int):
    """指定されたIDのブログ記事を更新します。"""
    post = BlogPost.query.get_or_404(post_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON input."}), 400

    try:
        # リクエストデータに基づいてフィールドを更新
        post.title = data.get('title', post.title)
        post.content = data.get('content', post.content)
        post.status = data.get('status', post.status)
        post.quality_check_status = data.get('quality_check_status', post.quality_check_status)
        post.updated_at = datetime.utcnow()

        db.session.commit()
        logger.info(f"Post {post_id} updated successfully.")
        return jsonify(post.to_dict()), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error while updating post {post_id}: {e}", exc_info=True)
        return jsonify({"error": "Database error occurred."}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error while updating post {post_id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred."}), 500


@posts_bp.route('/posts/<int:post_id>/publish', methods=['POST'])
def publish_post(post_id: int):
    """
    指定されたIDのブログ記事をはてなブログに公開します。
    注意: このエンドポイントはデモ用であり、実際の公開処理は
    `article_orchestrator`サービスを介して行うことが推奨されます。
    """
    post = BlogPost.query.get_or_404(post_id)

    if post.status == 'published':
        return jsonify({"message": "Post is already published.", "url": post.hatena_entry_url}), 200

    try:
        # ここでは実際の公開処理は行わず、ダミーのレスポンスを返します。
        # 実際の公開ロジックは `hatena_service` を使用します。
        # 例:
        # from src.services.hatena_service import HatenaService
        # hatena = HatenaService(blog_id=post.blog_id)
        # entry = hatena.publish_article(post.title, post.content)
        
        # --- ダミーのレスポンス ---
        entry = {
            'id': f'dummy-entry-id-{post_id}',
            'url': f'https://example.com/blog/entry/{post_id}'
        }
        # --- ここまで --- 

        if entry and entry.get('id'):
            # データベースのステータスを更新
            post.status = 'published'
            post.hatena_entry_id = entry['id']
            post.hatena_entry_url = entry['url']
            post.published_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Post {post_id} was marked as published (dummy). URL: {entry['url']}")
            return jsonify({"message": "Post published successfully (dummy).", "url": entry['url']}), 200
        else:
            logger.error(f"Failed to publish post {post_id}. Dummy entry generation failed.")
            return jsonify({"error": "Failed to publish post (dummy)."}), 500

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error while publishing post {post_id}: {e}", exc_info=True)
        return jsonify({"error": "Database error occurred."}), 500
    except Exception as e:
        logger.error(f"Error publishing post {post_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
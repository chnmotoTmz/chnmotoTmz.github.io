"""
Blog Analytics Dashboard API

データベースとログファイルから投稿履歴を集計し、
可視化ダッシュボードを提供します。
"""

import logging
import os
import re
from datetime import datetime, timedelta
from collections import Counter
from flask import Blueprint, jsonify, render_template
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from src.database import db, BlogPost, Blog

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates')


@dashboard_bp.route('/dashboard')
def dashboard_view():
    """ダッシュボードHTMLページを表示"""
    return render_template('dashboard.html')


@dashboard_bp.route('/dashboard/api/stats')
def dashboard_stats():
    """
    ダッシュボード用の統計データをJSON形式で返す
    
    Returns:
        - posts_per_blog: ブログ別投稿数
        - posts_timeline: 日別投稿数（直近30日）
        - status_distribution: ステータス別分布
        - top_keywords: タイトルから抽出した頻出キーワード
        - recent_topics: ログから抽出した最近のトピック
    """
    try:
        stats = {}
        
        # 1. ブログ別投稿数
        posts_per_blog = db.session.query(
            Blog.name,
            func.count(BlogPost.id).label('count')
        ).join(BlogPost, BlogPost.blog_id == Blog.id)\
         .group_by(Blog.name)\
         .order_by(func.count(BlogPost.id).desc())\
         .all()
        
        stats['posts_per_blog'] = [
            {'blog': name, 'count': count} 
            for name, count in posts_per_blog
        ]
        
        # 2. 日別投稿数（直近30日）
        thirty_days_ago = datetime.now() - timedelta(days=30)
        # SQLite specific date function usage might be needed if not using standard SQL
        # Assuming standard SQL or SQLite compatible func.date
        posts_timeline = db.session.query(
            func.date(BlogPost.created_at).label('date'),
            func.count(BlogPost.id).label('count')
        ).filter(BlogPost.created_at >= thirty_days_ago)\
         .group_by(func.date(BlogPost.created_at))\
         .order_by(func.date(BlogPost.created_at))\
         .all()
        
        stats['posts_timeline'] = [
            {'date': str(date), 'count': count}
            for date, count in posts_timeline
        ]
        
        # 3. ステータス別分布
        status_dist = db.session.query(
            BlogPost.status,
            func.count(BlogPost.id).label('count')
        ).group_by(BlogPost.status).all()
        
        stats['status_distribution'] = [
            {'status': status or 'unknown', 'count': count}
            for status, count in status_dist
        ]
        
        # 4. タイトルから頻出キーワード抽出
        recent_posts = BlogPost.query.order_by(
            BlogPost.created_at.desc()
        ).limit(100).all()
        
        all_words = []
        for post in recent_posts:
            # 日本語タイトルから名詞的な単語を抽出（簡易版）
            # 漢字・ひらがな・カタカナの連続を単語とみなす
            words = re.findall(r'[一-龥ァ-ヶー]+|[a-zA-Z0-9]+', post.title)
            # 助詞などを除外するための簡易フィルタ（2文字以上）
            all_words.extend([w for w in words if len(w) >= 2])
        
        keyword_counter = Counter(all_words)
        stats['top_keywords'] = [
            {'keyword': word, 'count': count}
            for word, count in keyword_counter.most_common(20)
        ]
        
        # 5. ログファイルから最近のトピックを抽出
        stats['recent_topics'] = extract_recent_topics_from_logs()
        
        return jsonify(stats)
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in dashboard stats: {e}", exc_info=True)
        return jsonify({'error': 'Database query failed'}), 500
    except Exception as e:
        logger.error(f"Unexpected error in dashboard stats: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


def extract_recent_topics_from_logs(days=7, max_files=50):
    """
    ログファイルから最近のトピックを抽出
    
    Args:
        days: 何日前までのログを読むか
        max_files: 最大で読み込むファイル数
    
    Returns:
        List of dict with topic info
    """
    topics = []
    # プロジェクトルートからの相対パスを想定
    # src/routes_dashboard.py から見て ../../logs/revision_io
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    log_dir = os.path.join(base_dir, 'logs', 'revision_io')
    
    if not os.path.exists(log_dir):
        logger.warning(f"Log directory not found: {log_dir}")
        return topics
    
    try:
        # 直近のログファイルを取得
        cutoff_date = datetime.now() - timedelta(days=days)
        files = []
        
        for filename in os.listdir(log_dir):
            if not filename.endswith('_response.txt'):
                continue
            
            # ファイル名から日時を抽出 (例: 20251125_193524_753516_response.txt)
            match = re.match(r'(\d{8})_(\d{6})_\d+_response\.txt', filename)
            if not match:
                continue
            
            date_str = match.group(1)
            time_str = match.group(2)
            try:
                file_datetime = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
                
                if file_datetime >= cutoff_date:
                    files.append((file_datetime, filename))
            except ValueError:
                continue
        
        # 新しい順にソートして最大件数まで
        files.sort(reverse=True)
        files = files[:max_files]
        
        # ファイルからタイトルを抽出
        for file_datetime, filename in files:
            filepath = os.path.join(log_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # 先頭1000文字のみ読む
                
                # タイトルを抽出
                title_match = re.search(r'【修正タイトル】\s*\n(.+)', content)
                if title_match:
                    title = title_match.group(1).strip()
                    topics.append({
                        'timestamp': file_datetime.isoformat(),
                        'title': title,
                        'date': file_datetime.strftime('%Y-%m-%d %H:%M')
                    })
            except Exception as e:
                logger.warning(f"Failed to parse log file {filename}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error extracting topics from logs: {e}", exc_info=True)
    
    return topics

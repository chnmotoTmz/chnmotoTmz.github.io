"""
Logs Dashboard API

ログファイルの閲覧と検索を提供するダッシュボード
"""

import logging
import os
import json
from pathlib import Path
from flask import Blueprint, jsonify, render_template, request
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)
logs_bp = Blueprint('logs', __name__, template_folder='templates')

LOGS_POSTS_DIR = Path("logs/posts")

@logs_bp.route('/logs')
def logs_dashboard():
    """ログダッシュボードHTMLページを表示"""
    return render_template('logs_dashboard.html')

@logs_bp.route('/api/logs/files')
def get_log_files():
    """ログファイル一覧をJSONで返す"""
    try:
        if not LOGS_POSTS_DIR.exists():
            return jsonify([])

        files = []
        for file_path in LOGS_POSTS_DIR.glob("*.jsonl"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "modified_str": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })

        # 最新のファイルが先頭に来るようにソート
        files.sort(key=lambda x: x["modified"], reverse=True)
        return jsonify(files)

    except Exception as e:
        logger.error(f"ログファイル一覧取得エラー: {e}")
        return jsonify([]), 500

@logs_bp.route('/api/logs/content/<filename>')
def get_log_content(filename):
    """指定したログファイルの内容をJSONで返す"""
    try:
        limit = int(request.args.get('limit', 50))
        file_path = LOGS_POSTS_DIR / filename

        if not file_path.exists():
            return jsonify({"error": "ファイルが見つかりません"}), 404

        if not file_path.is_file():
            return jsonify({"error": "指定されたパスはファイルではありません"}), 400

        entries = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError as e:
                        # JSONパースエラーの場合はテキストとして追加
                        entries.append({
                            "error": f"JSONパースエラー: {str(e)}",
                            "raw_content": line[:200] + "..." if len(line) > 200 else line
                        })

        return jsonify(entries)

    except Exception as e:
        logger.error(f"ログ内容取得エラー: {e}")
        return jsonify({"error": str(e)}), 500

@logs_bp.route('/api/logs/search/<filename>')
def search_log_content(filename):
    """指定したログファイル内で検索"""
    try:
        query = request.args.get('query', '')
        limit = int(request.args.get('limit', 20))

        if not query:
            return jsonify({"error": "検索クエリが必要です"}), 400

        file_path = LOGS_POSTS_DIR / filename

        if not file_path.exists():
            return jsonify({"error": "ファイルが見つかりません"}), 404

        matching_entries = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and query.lower() in line.lower():
                    try:
                        entry = json.loads(line)
                        matching_entries.append(entry)
                        if len(matching_entries) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue

        return jsonify(matching_entries)

    except Exception as e:
        logger.error(f"ログ検索エラー: {e}")
        return jsonify({"error": str(e)}), 500
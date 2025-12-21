from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import json
from pathlib import Path
from typing import List, Dict, Any

router = APIRouter()

LOGS_POSTS_DIR = Path("logs/posts")

@router.get("/api/logs/posts")
async def list_log_files() -> List[Dict[str, Any]]:
    """
    logs/postsディレクトリのログファイル一覧を返す
    """
    try:
        if not LOGS_POSTS_DIR.exists():
            return []

        files = []
        for file_path in LOGS_POSTS_DIR.glob("*.jsonl"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })

        # 最新のファイルが先頭に来るようにソート
        files.sort(key=lambda x: x["modified"], reverse=True)
        return files

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ログファイル一覧取得エラー: {str(e)}")

@router.get("/api/logs/posts/{filename}")
async def get_log_content(filename: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    指定したログファイルの内容を返す
    limit: 取得するエントリ数の上限（デフォルト50）
    """
    try:
        file_path = LOGS_POSTS_DIR / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="ログファイルが見つかりません")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="指定されたパスはファイルではありません")

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

        return entries

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ログ内容取得エラー: {str(e)}")

@router.get("/api/logs/posts/{filename}/search")
async def search_log_content(filename: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    指定したログファイル内でクエリにマッチするエントリを検索
    """
    try:
        file_path = LOGS_POSTS_DIR / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="ログファイルが見つかりません")

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

        return matching_entries

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ログ検索エラー: {str(e)}")
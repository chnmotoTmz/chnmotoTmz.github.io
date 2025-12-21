import os
import re
import yaml
from typing import Dict, Any
from sqlalchemy.orm import sessionmaker

from src.database import db, Blog


def _resolve_env_placeholders(value: Any) -> Any:
    """${ENV_VAR} を実際の環境変数で展開する。辞書/配列/文字列を再帰的に処理。"""
    if isinstance(value, str):
        # ${VAR_NAME} を検出して置換
        def repl(match: re.Match) -> str:
            var = match.group(1)
            return os.getenv(var, '')

        return re.sub(r"\$\{([^}]+)\}", repl, value)
    if isinstance(value, dict):
        return {k: _resolve_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(v) for v in value]
    return value


def initialize_blog_config(yaml_path: str = 'blogs.yml') -> int:
    """
    blogs.yml からブログ設定を読み込み、DB の blogs テーブルに upsert する。

    - ${ENV_VAR} 形式のプレースホルダは環境変数で展開する。
    - 既存の .env.* 依存は廃止する。

    Args:
        yaml_path: 設定ファイルパス（デフォルト 'blogs.yml'）

    Returns:
        upsert 件数
    """
    if not os.path.exists(yaml_path):
        print(f"[BlogConfig] {yaml_path} が見つかりません。スキップします。")
        return 0

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    blogs_map: Dict[str, Dict[str, Any]] = data.get('blogs', {})
    if not blogs_map:
        print(f"[BlogConfig] {yaml_path} に blogs セクションがありません。スキップします。")
        return 0

    Session = sessionmaker(bind=db.engine)
    session = Session()
    upserts = 0
    try:
        for key, conf in blogs_map.items():
            conf = _resolve_env_placeholders(conf)

            hatena_id = (conf.get('hatena_id') or '').strip()
            hatena_blog_id = (conf.get('hatena_blog_id') or '').strip()
            api_key = (conf.get('hatena_api_key') or conf.get('api_key') or '').strip()
            blog_name = (conf.get('blog_name') or key).strip()

            if not (hatena_id and hatena_blog_id and api_key):
                print(f"[BlogConfig] 不完全な設定のためスキップ: key={key}, blog_id='{hatena_blog_id}'")
                continue

            # hatena_blog_id はユニーク
            blog: Blog | None = session.query(Blog).filter_by(hatena_blog_id=hatena_blog_id).one_or_none()
            if blog:
                changed = False
                if blog.name != blog_name:
                    blog.name = blog_name
                    changed = True
                if blog.hatena_id != hatena_id:
                    blog.hatena_id = hatena_id
                    changed = True
                if blog.api_key != api_key:
                    blog.api_key = api_key
                    changed = True
                if changed:
                    session.commit()
                    upserts += 1
                    print(f"[BlogConfig] 更新: {blog_name} ({hatena_blog_id})")
                else:
                    print(f"[BlogConfig] 変更なし: {blog_name} ({hatena_blog_id})")
            else:
                blog = Blog(
                    name=blog_name,
                    hatena_id=hatena_id,
                    hatena_blog_id=hatena_blog_id,
                    api_key=api_key,
                )
                session.add(blog)
                session.commit()
                upserts += 1
                print(f"[BlogConfig] 追加: {blog_name} ({hatena_blog_id})")
    finally:
        session.close()

    return upserts

# #!/usr/bin/env python3
# """
# Blog initialization utility
# Loads blog configuration from environment variables and updates database
# """
# import os
# import logging
# from src.database import db, Blog

# logger = logging.getLogger(__name__)

# def initialize_blog_config():
#     """
#     Initialize or update blog configuration from environment variables
#     """
#     try:
#         # Get blog configuration from environment
#         hatena_blog_id = os.getenv('HATENA_BLOG_ID')
#         hatena_id = os.getenv('HATENA_ID')
#         hatena_api_key = os.getenv('HATENA_API_KEY')
#         blog_name = os.getenv('HATENA_BLOGNAME', 'Default Blog')
        
#         if not hatena_blog_id:
#             logger.warning("HATENA_BLOG_ID not set in environment variables")
#             return None
        
#         # Find or create blog entry
#         blog = Blog.query.filter_by(hatena_blog_id=hatena_blog_id).first()
        
#         if blog:
#             # Update existing blog with current environment values
#             updated = False
#             if blog.name != blog_name:
#                 blog.name = blog_name
#                 updated = True
            
#             if updated:
#                 db.session.commit()
#                 logger.info(f"Updated blog configuration: {hatena_blog_id}")
#             else:
#                 logger.info(f"Blog configuration up to date: {hatena_blog_id}")
#         else:
#             # Create new blog entry
#             blog = Blog(
#                 name=blog_name,
#                 hatena_blog_id=hatena_blog_id
#             )
#             db.session.add(blog)
#             db.session.commit()
#             logger.info(f"Created new blog configuration: {hatena_blog_id} (ID: {blog.id})")
        
#         # Log the configuration (without sensitive data)
#         logger.info(f"Blog API configuration loaded:")
#         logger.info(f"  Blog ID: {hatena_blog_id}")
#         logger.info(f"  Hatena ID: {hatena_id}")
#         logger.info(f"  API Key: {'*' * len(hatena_api_key) if hatena_api_key else 'Not set'}")
#         logger.info(f"  Blog Name: {blog_name}")
        
#         return blog
        
#     except Exception as e:
#         logger.error(f"Failed to initialize blog configuration: {e}", exc_info=True)
#         return None
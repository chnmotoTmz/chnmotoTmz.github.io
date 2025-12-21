"""
Blog configuration synchronization utility.

Syncs blog configuration from environment variables to the database.
This ensures that Hatena blog credentials are available for article publishing.
"""

import logging
import os
from typing import List, Tuple
from src.database import db, Blog

logger = logging.getLogger(__name__)


def sync_blog_config_from_env() -> Tuple[int, int]:
    """
    Synchronize blog configurations from environment variables to the database.
    
    Supports two patterns:
    1. Single blog (legacy):
       - HATENA_ID, HATENA_BLOG_ID, HATENA_API_KEY, HATENA_BLOGNAME
    2. Multi-blog (new):
       - HATENA_ID_<suffix>, HATENA_BLOG_ID_<suffix>, HATENA_API_KEY_<suffix>, HATENA_BLOGNAME_<suffix>
    
    Returns:
        Tuple[int, int]: (created_count, updated_count)
    """
    created = 0
    updated = 0
    
    # Pattern 1: Single blog (legacy, for backward compatibility)
    hatena_id = os.getenv('HATENA_ID')
    hatena_blog_id = os.getenv('HATENA_BLOG_ID')
    api_key = os.getenv('HATENA_API_KEY')
    blog_name = os.getenv('HATENA_BLOGNAME', 'Default Blog')
    
    if hatena_id and hatena_blog_id and api_key:
        result = _sync_single_blog(hatena_id, hatena_blog_id, api_key, blog_name)
        if result == 'created':
            created += 1
        elif result == 'updated':
            updated += 1
    
    # Pattern 2: Multi-blog configuration
    # Look for HATENA_BLOG_ID_<suffix> patterns
    for key, value in os.environ.items():
        if key.startswith('HATENA_BLOG_ID_'):
            suffix = key[len('HATENA_BLOG_ID_'):]  # Extract suffix
            
            # Get corresponding values for this suffix
            hatena_id_key = f'HATENA_ID_{suffix}'
            api_key_key = f'HATENA_API_KEY_{suffix}'
            blog_name_key = f'HATENA_BLOGNAME_{suffix}'
            
            hatena_id = os.getenv(hatena_id_key)
            hatena_blog_id = value
            api_key = os.getenv(api_key_key)
            blog_name = os.getenv(blog_name_key, f'Blog {suffix}')
            
            if hatena_id and hatena_blog_id and api_key:
                result = _sync_single_blog(hatena_id, hatena_blog_id, api_key, blog_name)
                if result == 'created':
                    created += 1
                elif result == 'updated':
                    updated += 1
    
    return created, updated


def _sync_single_blog(hatena_id: str, hatena_blog_id: str, api_key: str, blog_name: str) -> str:
    """
    Sync a single blog configuration to the database.
    
    Args:
        hatena_id: Hatena user ID
        hatena_blog_id: Hatena blog ID (unique)
        api_key: Hatena Atom API key
        blog_name: Blog display name
    
    Returns:
        str: 'created', 'updated', or 'unchanged'
    """
    try:
        # Check if blog already exists (by hatena_blog_id which is unique)
        blog = Blog.query.filter_by(hatena_blog_id=hatena_blog_id).first()
        
        if blog:
            # Update existing blog with latest credentials
            changed = False
            
            if blog.hatena_id != hatena_id:
                blog.hatena_id = hatena_id
                changed = True
            
            if blog.api_key != api_key:
                blog.api_key = api_key
                changed = True
            
            if blog.name != blog_name:
                blog.name = blog_name
                changed = True
            
            if changed:
                db.session.commit()
                logger.info(f"Updated blog config: {blog_name} (ID: {hatena_blog_id})")
                return 'updated'
            else:
                logger.debug(f"Blog config unchanged: {blog_name} (ID: {hatena_blog_id})")
                return 'unchanged'
        else:
            # Create new blog entry
            blog = Blog(
                name=blog_name,
                hatena_id=hatena_id,
                hatena_blog_id=hatena_blog_id,
                api_key=api_key,
            )
            db.session.add(blog)
            db.session.commit()
            logger.info(f"Created blog config: {blog_name} (ID: {hatena_blog_id})")
            return 'created'
    
    except Exception as e:
        logger.error(f"Failed to sync blog config {hatena_blog_id}: {e}", exc_info=True)
        db.session.rollback()
        return 'failed'


__all__ = ['sync_blog_config_from_env']

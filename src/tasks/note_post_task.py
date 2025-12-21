"""
Note Post Task - Posts article as a draft to note.com.
"""

import logging
import os
import json
from typing import Dict, Any, Optional
from src.framework.base_task import BaseTaskModule
from src.services.note_service import NoteService

logger = logging.getLogger(__name__)


class NotePostTask(BaseTaskModule):
    """Posts article as a draft to note.com"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.note_service = None
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not self.note_service:
                cookies_json = os.getenv('NOTE_COOKIES', '{}')
                try:
                    cookies = json.loads(cookies_json)
                except json.JSONDecodeError:
                    logger.error("Invalid NOTE_COOKIES JSON.")
                    return {"note_post_status": "failed"}
                
                if not cookies:
                    logger.warning("NOTE_COOKIES not configured. Skipping.")
                    return {"note_post_status": "skipped"}
                
                self.note_service = NoteService(cookies)
            
            title = context.get('title', 'Untitled')
            article_content = context.get('content', '') or context.get('article_content', '')
            thumbnail_path = context.get('thumbnail_path')
            
            if not article_content:
                logger.warning("No content found. Skipping.")
                return {"note_post_status": "skipped"}
            
            logger.info(f"Posting to note.com: {title}")
            success = self.note_service.post_to_note_draft(
                title=title,
                markdown_content=article_content,
                image_path=thumbnail_path
            )
            
            return {"note_post_status": "success" if success else "failed"}
            
        except Exception as e:
            logger.error(f"Error in NotePostTask: {e}", exc_info=True)
            return {"note_post_status": "error", "note_post_error": str(e)}
    
    @staticmethod
    def get_module_info() -> Dict[str, Any]:
        return {
            'name': 'NotePost',
            'description': 'Posts the article as a draft to note.com'
        }
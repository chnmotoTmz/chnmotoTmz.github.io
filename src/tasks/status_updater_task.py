from typing import Dict, Any
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from src.framework.base_task import BaseTaskModule
from src.database import db, BlogPost

class StatusUpdaterTask(BaseTaskModule):
    """
    Updates the status of a blog post in the database.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        post_id: int = inputs.get("post_id")
        hatena_entry: Dict = inputs.get("hatena_entry")

        if not post_id or not hatena_entry:
            raise ValueError("Missing post_id or hatena_entry.")

        try:
            post = db.session.query(BlogPost).get(post_id)
            if not post:
                return {}

            post.status = 'published'
            post.hatena_entry_id = hatena_entry.get('id')
            post.hatena_entry_url = hatena_entry.get('url')
            post.published_at = datetime.utcnow()

            db.session.commit()

            return {
                "final_post_title": post.title,
                "final_post_url": post.hatena_entry_url
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "final_post_title": "Unknown Title",
                "final_post_url": hatena_entry.get('url', 'N/A')
            }

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "StatusUpdater",
            "description": "Updates blog post status to 'published'."
        }
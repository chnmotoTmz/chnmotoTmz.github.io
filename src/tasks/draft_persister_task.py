import logging
from typing import Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError

from src.framework.base_task import BaseTaskModule
from src.database import db, BlogPost, PostSourceMessage

logger = logging.getLogger(__name__)

class DraftPersisterTask(BaseTaskModule):
    """
    Persists the generated article as a draft in the database.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves the article title and content to the BlogPost table.

        Args:
            inputs (Dict[str, Any]): Expects 'blog' (dict), 'user' (dict),
                                     'title' (str), 'content' (str), and
                                     'message_ids' (List[Any]).

        Returns:
            Dict[str, Any]: A dictionary containing the 'post_id' of the new draft.
        """
        blog_data: Dict = inputs.get("blog")
        user_data: Dict = inputs.get("user")
        title: str = inputs.get("title")
        content: str = inputs.get("content")
        message_ids: List[Any] = inputs.get("message_ids")

        # Allow message_ids to be an empty list, but it must be present (not None)
        if not all([blog_data, user_data, title, content]) or message_ids is None:
            # Log which inputs are missing and return gracefully to avoid stopping the workflow
            missing = []
            if not blog_data:
                missing.append('blog')
            if not user_data:
                missing.append('user')
            if not title:
                missing.append('title')
            if not content:
                missing.append('content')
            if message_ids is None:
                missing.append('message_ids')
            # Use logging to surface the issue but do not raise to keep workflows resilient
            logger.warning(f"DraftPersisterTask: missing required inputs, skipping persist: {missing}")
            # Return explicit None to denote that no draft was created so downstream tasks can handle it
            return {"post_id": None} 

        try:
            post = BlogPost(
                blog_id=blog_data['id'],
                author_id=user_data['id'],
                title=title,
                content=content,
                status='draft'
            )
            db.session.add(post)
            db.session.flush()  # To get post.id before commit

            actual_ids = [msg['id'] for msg in message_ids if isinstance(msg, dict) and 'id' in msg] if isinstance(message_ids[0], dict) else message_ids

            for msg_id in actual_ids:
                source_msg = PostSourceMessage(post_id=post.id, message_id=msg_id)
                db.session.add(source_msg)

            db.session.commit()

            return {"post_id": post.id}

        except SQLAlchemyError as e:
            db.session.rollback()
            raise ConnectionError(f"Failed to persist draft to database: {e}") from e

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        """Returns metadata about the module."""
        return {
            "name": "DraftPersister",
            "description": "Saves the generated article as a draft in the database.",
            "inputs": {
                "blog": "Dict",
                "user": "Dict",
                "title": "str",
                "content": "str",
                "message_ids": "List[Any]"
            },
            "outputs": {
                "post_id": "int"
            }
        }

import logging
from typing import Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError

from src.framework.base_task import BaseTaskModule
from src.database import db, BlogPost, PostSourceMessage, Blog, User

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
            # Resolve blog DB id: accept either a DB-style dict with 'id' or a YAML config dict containing 'hatena_blog_id'
            if 'id' in blog_data:
                blog_id = blog_data['id']
            elif 'hatena_blog_id' in blog_data:
                hatena = blog_data.get('hatena_blog_id')
                blog_entry = db.session.query(Blog).filter_by(hatena_blog_id=hatena).first()
                if not blog_entry:
                    # Try to create a DB entry from YAML-like config
                    try:
                        blog_entry = Blog(
                            name=blog_data.get('blog_name', 'Unknown'),
                            hatena_id=blog_data.get('hatena_id', ''),
                            hatena_blog_id=hatena,
                            api_key=blog_data.get('hatena_api_key', blog_data.get('api_key', ''))
                        )
                        db.session.add(blog_entry)
                        db.session.commit()
                    except SQLAlchemyError as e:
                        db.session.rollback()
                        logger.warning("Failed to create Blog DB entry: %s", e)
                        return {"post_id": None}
                blog_id = blog_entry.id
            else:
                logger.warning("DraftPersisterTask: blog data has no 'id' or 'hatena_blog_id', skipping persist")
                return {"post_id": None}

            # Resolve author id: prefer explicit 'id', else try to find/create by line_user_id
            if 'id' in user_data:
                author_id = user_data['id']
            else:
                line_uid = user_data.get('line_user_id') or user_data.get('line_id')
                if not line_uid:
                    logger.warning("DraftPersisterTask: user has no 'id' or 'line_user_id', skipping persist")
                    return {"post_id": None}
                user_entry = db.session.query(User).filter_by(line_user_id=line_uid).first()
                if not user_entry:
                    try:
                        user_entry = User(line_user_id=line_uid, display_name=user_data.get('display_name', ''))
                        db.session.add(user_entry)
                        db.session.commit()
                    except SQLAlchemyError as e:
                        db.session.rollback()
                        logger.warning("Failed to create User DB entry: %s", e)
                        return {"post_id": None}
                author_id = user_entry.id

            post = BlogPost(
                blog_id=blog_id,
                author_id=author_id,
                title=title,
                content=content,
                status='draft'
            )
            db.session.add(post)
            db.session.flush()  # To get post.id before commit

            # Normalize message_ids: accept list of dicts or list of ids, and handle empty lists
            actual_ids = []
            if message_ids:
                if isinstance(message_ids[0], dict):
                    actual_ids = [msg['id'] for msg in message_ids if isinstance(msg, dict) and 'id' in msg]
                else:
                    actual_ids = list(message_ids)

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

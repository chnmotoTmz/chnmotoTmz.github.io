from typing import Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError

from src.framework.base_task import BaseTaskModule
from src.database import db, User, Blog, Message, Asset

class DatabaseFetcherTask(BaseTaskModule):
    """
    Task to fetch necessary data for an article batch from the database.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetches user, blog, messages, and assets from the database.

        Args:
            inputs (Dict[str, Any]): Expects 'user_id' and 'message_ids'.

        Returns:
            Dict[str, Any]: Contains 'user', 'blog', 'messages', and 'assets' data as dicts.
        """
        user_id = inputs.get("user_id")
        message_ids = inputs.get("message_ids")

        if not user_id or not message_ids:
            raise ValueError("user_id and message_ids are required inputs.")

        try:
            if message_ids and isinstance(message_ids[0], dict):
                actual_ids = [msg['id'] for msg in message_ids if isinstance(msg, dict) and 'id' in msg]
            else:
                actual_ids = message_ids

            messages_query = Message.query.filter(Message.id.in_(actual_ids)).order_by(Message.created_at.asc()).all()
            if not messages_query:
                raise ValueError(f"No messages found for IDs: {actual_ids}")

            user_query = User.query.get(user_id)
            blog_query = Blog.query.first()

            if not user_query or not blog_query:
                raise ValueError(f"User or Blog not found for User ID: {user_id}")

            assets_query = Asset.query.join(Message).filter(Message.id.in_(actual_ids)).all()

            def to_dict(obj):
                if obj is None:
                    return None
                # A simple serializer that ignores non-serializable attributes
                return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

            return {
                "user": to_dict(user_query),
                "blog": to_dict(blog_query),
                "messages": [to_dict(m) for m in messages_query],
                "assets": [to_dict(a) for a in assets_query],
                "message_ids": message_ids # Pass original message_ids through
            }

        except SQLAlchemyError as e:
            raise ConnectionError(f"Database fetch failed: {e}") from e

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        """Returns metadata about the module."""
        return {
            "name": "DatabaseFetcher",
            "description": "Fetches batch data (user, blog, messages, assets) from the database.",
            "inputs": {
                "user_id": "int",
                "message_ids": "List[Any]"
            },
            "outputs": {
                "user": "Dict",
                "blog": "Dict",
                "messages": "List[Dict]",
                "assets": "List[Dict]",
                "message_ids": "List[Any]"
            }
        }

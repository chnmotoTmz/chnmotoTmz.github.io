"""
DEPRECATED: Legacy ArticleProcessingService shim.

This module is kept temporarily to avoid import-time errors while migrating to
WorkflowProcessingService. All calls are delegated to the workflow.
"""

import logging
import os
from typing import Any, List, Optional

from src.database import User

logger = logging.getLogger(__name__)


class ArticleProcessingService:
    """Deprecated orchestrator. Delegates to WorkflowProcessingService."""

    def __init__(self, *args, **kwargs) -> None:
        logger.warning(
            "ArticleProcessingService is deprecated. Use WorkflowProcessingService instead."
        )

    def process_user_batch(self, user_id: int, message_ids: List[Any], channel_id: str = None) -> None:
        """Delegate to the JSON-defined workflow path and return."""
        try:
            use_workflow = os.getenv('USE_WORKFLOW', 'true').lower() in ('1', 'true', 'yes')
            if not use_workflow:
                logger.info("USE_WORKFLOW disabled; nothing to do in deprecated orchestrator.")
                return

            from src.services.workflow_processing_service import WorkflowProcessingService

            user_obj: Optional[User] = User.query.get(user_id)
            if not user_obj:
                logger.error("Workflow delegation failed: user not found (user_id=%s)", user_id)
                return

            logger.info(
                "Delegating to WorkflowProcessingService (line_user_id=%s)", user_obj.line_user_id
            )
            WorkflowProcessingService().process_user_batch(
                line_user_id=user_obj.line_user_id,
                message_ids=message_ids,
                channel_id=channel_id,
            )
        except Exception as e:
            logger.error("Workflow delegation failed in deprecated orchestrator: %s", e, exc_info=True)
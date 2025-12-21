import os
import logging
from typing import List, Any
from datetime import datetime

from src.framework.task_runner import TaskRunner
from src.services.framework.service_registry import service_registry
from src.utils import gemini_logger

logger = logging.getLogger(__name__)


class WorkflowProcessingService:
    """
    A service to execute dynamic, JSON-defined workflows.
    """

    def __init__(self):
        """
        Initializes the service and discovers all available task modules.
        """
        # Discover and register all task modules upon initialization.
        # Include the new src/tasks directory
        module_path = os.path.join(os.path.dirname(__file__), 'tasks')
        new_tasks_path = os.path.join(os.path.dirname(__file__), '..', 'tasks')
        service_registry.discover_modules([module_path, new_tasks_path])
        logger.info(f"Discovered modules in: {module_path} and {new_tasks_path}")

        # RagSimilarArticlesFetcherを明示的に登録
        try:
            from src.services.tasks.rag_similar_articles_fetcher import RagSimilarArticlesFetcher
            service_registry.register_module("RagSimilarArticlesFetcher", RagSimilarArticlesFetcher)
            logger.info("Manually registered RagSimilarArticlesFetcher module.")
        except Exception as e:
            logger.error(f"Failed to manually register RagSimilarArticlesFetcher: {e}")
        
        # AffiliateLinkerTaskを明示的に登録
        try:
            from src.services.tasks.affiliate_linker_task import AffiliateLinkerTask
            service_registry.register_module("AffiliateLinkerTask", AffiliateLinkerTask)
            logger.info("Manually registered AffiliateLinkerTask module.")
        except Exception as e:
            logger.error(f"Failed to manually register AffiliateLinkerTask: {e}")
        

    def process_user_batch(self, line_user_id: str, message_ids: List[Any], channel_id: str = None) -> None:
        """
        Processes a user's batch of messages by running the article generation workflow.

        Args:
            line_user_id (str): The LINE user ID of the user.
            message_ids (List[Any]): A list of message IDs to be processed.
            channel_id (str): The LINE channel ID where the message was received (optional, defaults to None).
        """
        # Initialize Gemini interaction logging for this session
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Sanitize user_id for filename
        safe_user_id = "".join(c for c in line_user_id if c.isalnum() or c in ('-', '_'))
        log_filename = os.path.join("logs", "posts", f"gemini_{timestamp}_{safe_user_id}.jsonl")
        gemini_logger.set_log_file(log_filename)

        logger.info(f"Workflow service: Starting article generation for LINE user {line_user_id} on channel {channel_id or 'default'}.")
        logger.info(f"Gemini interactions will be logged to: {log_filename}")

        try:
            # Get user_id from line_user_id
            from src.database import User
            user = User.query.filter_by(line_user_id=line_user_id).first()
            if not user:
                raise ValueError(f"User not found for LINE user ID: {line_user_id}")
            user_id = user.id

            # Define the path to the workflow definition file
            # Use the new App definition if available, else fallback
            app_workflow_path = os.path.join(os.path.dirname(__file__), '..', 'apps', 'article_generation', 'workflow.json')
            if os.path.exists(app_workflow_path):
                workflow_path = app_workflow_path
            else:
                workflow_path = os.path.join(os.path.dirname(__file__), '..', 'workflows', 'article_generation_v2.json')

            logger.info(f"Using workflow definition: {os.path.abspath(workflow_path)}")

            # Initialize the runner with the specific workflow
            task_runner = TaskRunner(workflow_path=workflow_path)

            # Define the initial inputs required by the workflow
            initial_inputs = {
                "user_id": user_id,
                "message_ids": message_ids,
                "line_user_id": line_user_id,  # エラーハンドラで必要
                "channel_id": channel_id or "",  # ワークフローで必須なので必ず提供
            }
            
            # Execute the workflow
            result = task_runner.run(initial_inputs=initial_inputs)

            logger.info(f"Workflow for LINE user {line_user_id} completed. Final context keys: {list(result.keys())}")

        except Exception as e:
            logger.error(f"An unexpected error occurred during workflow execution for LINE user {line_user_id}: {e}", exc_info=True)
            # Further error handling or notifications could be triggered here if the
            # workflow's internal error handling fails.
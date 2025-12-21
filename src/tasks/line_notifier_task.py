from typing import Dict, Any, Optional
import logging
from src.framework.base_task import BaseTaskModule
from src.services.line_service import LineService

logger = logging.getLogger(__name__)

class LineNotifierTask(BaseTaskModule):
    """
    Sends a notification to the user via LINE.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.line_service = None

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        user_data: Dict = inputs.get("user") or {}
        line_user_id: str = inputs.get("line_user_id") or user_data.get("line_user_id")
        last_error_message: str = inputs.get("last_error_message")
        channel_id = inputs.get("channel_id")

        if not line_user_id:
            logger.error("No line_user_id provided. Cannot send notification.")
            return {}

        is_error = bool(last_error_message)
        
        if is_error:
            notification_message = f"Error during article creation:\n{last_error_message[:500]}"
        else:
            title: str = inputs.get("final_post_title", "Untitled")
            url: str = inputs.get("final_post_url")
            hatena_entry: Dict = inputs.get("hatena_entry") or {}
            if not url: url = hatena_entry.get("url", "")
            
            notification_message = f"Article published!\n\n\"{title}\"\n{url}"

        try:
            self.line_service = LineService(channel_id=channel_id) if channel_id else LineService()
            success = self.line_service.send_message(line_user_id, notification_message)
            if success:
                logger.info(f"Notification sent to {line_user_id}")
                logger.info(f"Message content:\n{notification_message}")
            else:
                logger.warning(f"Failed to send notification to {line_user_id}")
        except Exception as e:
            logger.error(f"Unexpected error in LineNotifierTask: {e}")

        return {}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "LineNotifier",
            "description": "Notifies the user via LINE."
        }
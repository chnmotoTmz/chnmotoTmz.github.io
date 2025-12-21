from typing import Dict, Any
from src.framework.base_task import BaseTaskModule
from src.services.line_service import LineService

class LineChatReplyTask(BaseTaskModule):
    """
    Sends a chat reply to the user via LINE.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.line_service = LineService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        line_user_id: str = inputs.get("line_user_id")
        reply: str = inputs.get("reply")
        last_error_message: str = inputs.get("last_error_message")
        channel_id: str = inputs.get("channel_id")

        if channel_id:
            self.line_service.set_channel(channel_id)

        if not line_user_id:
            return {}

        if last_error_message:
            notification_message = f"Error during chat processing:\n{last_error_message[:500]}"
            self.line_service.send_message(line_user_id, notification_message)
            return {}

        if reply:
            self.line_service.send_message(line_user_id, reply)
            
        return {}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "LineChatReplyTask",
            "description": "Sends a chat reply to the user via LINE."
        }
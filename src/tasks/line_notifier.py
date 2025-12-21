from src.framework.base_task import BaseTaskModule

class LineNotifier(BaseTaskModule):
    """
    Sends messages to LINE.
    """
    def __init__(self, config=None):
        super().__init__(config or {})
        from src.services.line_service import LineService
        self.line = LineService()

    def execute(self, inputs):
        user_id = inputs.get("line_user_id")
        if not user_id: return {}
        
        reply = inputs.get("reply") or inputs.get("last_error_message", "No message provided.")
        self.line.send_message(user_id, reply)
        return {}

    @classmethod
    def get_module_info(cls):
        return {
            "name": "LineNotifier",
            "description": "Sends messages to LINE.",
            "inputs": {"line_user_id": "str", "reply": "str (optional)", "last_error_message": "str (optional)"},
            "outputs": {}
        }
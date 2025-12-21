from typing import Dict, Any, List
from src.framework.base_task import BaseTaskModule

class ChatHistoryManager(BaseTaskModule):
    """
    Manages chat history for a user (in-memory, for demo/testing).
    """
    _history_store = {}

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        user_id = inputs.get("user_id")
        message = inputs.get("message")
        role = inputs.get("role", "user")
        if not user_id or not message:
            return {"history": []}
        history = self._history_store.setdefault(user_id, [])
        history.append({"role": role, "message": message})
        # Keep only last 10
        self._history_store[user_id] = history[-10:]
        return {"history": self._history_store[user_id]}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "ChatHistoryManager",
            "description": "Manages chat history for a user.",
            "inputs": {"user_id": "str", "message": "str", "role": "str (optional)"},
            "outputs": {"history": "list"}
        }

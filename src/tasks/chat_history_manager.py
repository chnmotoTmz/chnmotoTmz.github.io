from src.framework.base_task import BaseTaskModule

class ChatHistoryManager(BaseTaskModule):
    """
    ユーザーごとの会話履歴をメモリ上で管理するタスク（簡易版）
    """
    _histories = {}

    def __init__(self, config=None):
        super().__init__(config or {})

    def execute(self, inputs):
        user_id = inputs["user_id"]
        message = inputs["message"]
        role = inputs.get("role", "user")
        
        if user_id not in ChatHistoryManager._histories:
            ChatHistoryManager._histories[user_id] = []
            
        ChatHistoryManager._histories[user_id].append({"role": role, "content": message})
        return {"history": ChatHistoryManager._histories[user_id]}

    @classmethod
    def get_module_info(cls):
        return {
            "name": "ChatHistoryManager",
            "description": "Manages chat history per user.",
            "inputs": {"user_id": "str", "message": "str", "role": "str (optional)"},
            "outputs": {"history": "list"}
        }
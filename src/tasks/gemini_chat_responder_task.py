from typing import Dict, Any
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

class GeminiChatResponder(BaseTaskModule):
    """
    Generates an AI reply using Gemini, given the conversation history.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.gemini_service = GeminiService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        history = inputs.get("history", [])
        # Compose prompt from history
        prompt = "".join([
            f"{item['role']}: {item['message']}\n" for item in history
        ])

        # --- 最新ユーザー発話を参照し、�E然言語で持E�� ---
        user_utterances = [item['message'] for item in history if item.get('role') == 'user']
        last_user = user_utterances[-1] if user_utterances else ''

        reply = self.gemini_service.generate_text(prompt)
        return {"reply": reply}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "GeminiChatResponder",
            "description": "Generates an AI reply using Gemini with conversation history.",
            "inputs": {"history": "list"},
            "outputs": {"reply": "str"}
        }

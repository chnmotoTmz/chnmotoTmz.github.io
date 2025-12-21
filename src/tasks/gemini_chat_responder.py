from src.framework.base_task import BaseTaskModule

class GeminiChatResponder(BaseTaskModule):
    """Generates an AI response from Gemini given a conversation history."""
    def __init__(self, config=None):
        super().__init__(config or {})
        from src.services.gemini_service import GeminiService
        self.gemini = GeminiService()

    def execute(self, inputs):
        history = inputs["history"]
        prompt = ""
        for turn in history:
            if turn["role"] == "user":
                prompt += f"ユーザー: {turn['content']}\n"
            else:
                prompt += f"AI: {turn['content']}\n"
        prompt += "AI:"
        ai_reply = self.gemini.generate_text(prompt)
        return {"reply": ai_reply.strip()}

    @classmethod
    def get_module_info(cls):
        return {
            "name": "GeminiChatResponder",
            "description": "Generates an AI response from Gemini given a conversation history.",
            "inputs": {"history": "list"},
            "outputs": {"reply": "str"}
        }

from typing import Dict, Any, List
import logging
from src.framework.base_task import BaseTaskModule
from src.utils.command_parser import CommandParser, CommandContext
from src.services.buffer_service import BufferService
from src.services.line_service import LineService

logger = logging.getLogger(__name__)

class CommandParserTask(BaseTaskModule):
    """
    Parses commands from input text(s) and handles buffer operations.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.parser = CommandParser()
        self.buffer_service = BufferService()
        self.line_service = LineService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Handle various input formats for text
        texts: List[str] = []
        if "texts" in inputs and isinstance(inputs["texts"], list):
            texts = inputs["texts"]
        elif "initial_input" in inputs:
            texts = [str(inputs["initial_input"])]
        elif "text" in inputs:
            texts = [str(inputs["text"])]
            
        user_id = inputs.get("user_id", "default_user")
        line_user_id = inputs.get("line_user_id")
        channel_id = inputs.get("channel_id")
        
        logger.info("📥 CommandParserTask processing %d message(s)", len(texts))
        
        # Parse all messages together
        ctx: CommandContext = self.parser.parse_multi(texts)
        
        # Handle Buffer Save Operation
        if ctx.action == "SAVE_TO_BUFFER":
            self.buffer_service.save_to_buffer(user_id, ctx.buffer_slot, "\n".join(ctx.source_texts))
            message = f"✅ バッファ @{ctx.buffer_slot} に保存しました。"
            
            if line_user_id:
                self._notify_user(line_user_id, channel_id, message)

            return {
                "command_context": ctx.to_dict(),
                "cleaned_texts": [],
                "style_prompt": None,
                "stop_workflow": True,
                "message": message
            }

        # Handle Buffer Load Operation
        if ctx.action == "GENERATE_FROM_BUFFER":
            saved_content = self.buffer_service.get_from_buffer(user_id, ctx.buffer_slot)
            if not saved_content:
                message = f"⚠️ バッファ @{ctx.buffer_slot} は空です。"
                if line_user_id:
                    self._notify_user(line_user_id, channel_id, message)
                return {
                    "command_context": ctx.to_dict(),
                    "cleaned_texts": [],
                    "style_prompt": None,
                    "stop_workflow": True,
                    "message": message
                }
            # Inject buffer content as source
            ctx.source_texts = [saved_content]
            logger.info("📂 Loaded content from buffer @%d", ctx.buffer_slot)

        # Return parsed context for downstream tasks
        return {
            "command_context": ctx.to_dict(),
            "cleaned_texts": ctx.source_texts,
            "style_prompt": ctx.style_prompt,
            "stop_workflow": False,
            "message": None
        }

    def _notify_user(self, line_user_id: str, channel_id: str, message: str):
        """Send notification to LINE user."""
        try:
            self.line_service.push_message(line_user_id, message, channel_id)
        except Exception as e:
            logger.error("Failed to send notification: %s", e)

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "CommandParserTask",
            "description": "Parses commands from input text(s) and handles buffer operations.",
            "inputs": {
                "texts": "List[str]",
                "user_id": "Optional[str]",
                "line_user_id": "Optional[str]",
                "channel_id": "Optional[str]"
            },
            "outputs": {
                "command_context": "Dict",
                "cleaned_texts": "List[str]",
                "style_prompt": "Optional[str]",
                "stop_workflow": "bool",
                "message": "Optional[str]"
            }
        }
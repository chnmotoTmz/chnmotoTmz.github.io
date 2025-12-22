import logging
from typing import Dict, Any
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class ClearGeminiModeTask(BaseTaskModule):
    """
    Task to explicitly exit image generation mode and return to text mode.
    Used after thumbnail generation.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Exiting Gemini image mode to return to text input...")
        try:
            gemini_service = GeminiService()
            success = gemini_service.clear_image_mode()
            return {"clear_success": success}
        except Exception as e:
            logger.error(f"Failed to clear image mode: {e}")
            return {"clear_success": False, "error": str(e)}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "ClearGeminiMode", "description": "Exits image mode."}

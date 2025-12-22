import logging
import requests
from typing import Dict, Any
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class GeminiResetTask(BaseTaskModule):
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Triggering Gemini session reset...")
        try:
            gemini_service = GeminiService()
            # First, explicitly clear any image mode
            gemini_service.clear_image_mode()
            # Then start a new session
            success = gemini_service.start_new_session()
            return {"reset_success": success}
        except Exception as e:
            logger.error(f"Reset failed: {e}")
            return {"reset_success": False, "error": str(e)}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "GeminiReset", "description": "Resets Gemini session."}
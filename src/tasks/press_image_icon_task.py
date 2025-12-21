import logging
from typing import Dict, Any
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class PressImageIconTask(BaseTaskModule):
    """
    Task to instruct the browser extension to press the 'Create images' icon.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("🚀 Triggering 'Create images' icon press via extension...")
        
        try:
            gemini_service = GeminiService()
            success = gemini_service.press_image_icon()
            
            if success:
                logger.info("✅ Image icon press confirmed.")
            else:
                logger.warning("⚠️ Image icon press requested but confirmation failed.")
                
            return {"press_success": success}
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger image icon press: {e}")
            return {"press_success": False, "error": str(e)}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "PressImageIcon",
            "description": "Instructs the browser extension to press the 'Create images' icon."
        }

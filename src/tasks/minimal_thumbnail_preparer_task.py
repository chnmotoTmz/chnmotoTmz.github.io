from typing import Dict, Any
from src.framework.base_task import BaseTaskModule

class MinimalThumbnailPreparerTask(BaseTaskModule):
    """
    Creates a concise thumbnail prompt.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title = inputs.get('title', '')
        if not title:
            raise ValueError('Title is required.')

        prompt = f"Blog thumbnail for: \"{title}\". Clean design, high contrast, 16:9."
        return {'thumbnail_prompt': prompt}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "MinimalThumbnailPreparer",
            "description": "Generates a minimal thumbnail prompt."
        }
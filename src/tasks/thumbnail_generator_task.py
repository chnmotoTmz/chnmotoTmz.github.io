from typing import Dict, Any
import re
from src.framework.base_task import BaseTaskModule
from src.services.thumbnail_generator_service import ThumbnailGeneratorService

class ThumbnailGeneratorTask(BaseTaskModule):
    """
    Generates a thumbnail for an article and prepends it to the content.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.thumbnail_service = ThumbnailGeneratorService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title: str = inputs.get("title")
        content: str = inputs.get("content")
        thumbnail_prompt: str = inputs.get("thumbnail_prompt")

        if not title or not content:
            raise ValueError("Title and content are required inputs.")

        if not thumbnail_prompt:
            return {"enhanced_content": content}

        if re.match(r"^\s*!\\[.*?\\]\(http.*?\)", content):
            return {"enhanced_content": content}

        if not self.config.get('enabled', True):
            return {"enhanced_content": content}

        thumbnail_url = self.thumbnail_service.generate_and_upload(thumbnail_prompt)

        if not thumbnail_url:
            raise RuntimeError("Thumbnail generation failed: Service returned no URL.")

        thumbnail_markdown = f"![{title}]({thumbnail_url})\n\n"
        enhanced_content = thumbnail_markdown + content

        return {"enhanced_content": enhanced_content}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "ThumbnailGenerator",
            "description": "Generates a thumbnail image and prepends it to the article content.",
            "inputs": {
                "title": "str",
                "content": "str",
                "thumbnail_prompt": "str"
            },
            "outputs": {
                "enhanced_content": "str"
            }
        }
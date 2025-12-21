"""
StructuredArticleGeneratorTask - Generates an article from structured data.
"""
import logging
import re
from typing import Dict, Any, Optional

from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class StructuredArticleGeneratorTask(BaseTaskModule):
    """
    Generates article content from structured data using LLM.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_client = GeminiService()

    @staticmethod
    def get_module_info():
        return {
            "name": "StructuredArticleGeneratorTask",
            "description": "Generates an article from structured data."
        }

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        structured_data = inputs.get("structured_data")
        style_prompt = inputs.get("style_prompt")
        repost_context = inputs.get("repost_context")
        blog = inputs.get("blog")

        if not all([structured_data, repost_context, blog]):
            raise ValueError("Inputs 'structured_data', 'repost_context', and 'blog' are required.")
        
        logger.info("Generating article from structured data.")
        
        prompt = self._build_regeneration_prompt(
            structured_data, 
            style_prompt, 
            repost_context, 
            blog
        )
        
        response = self.llm_client.generate_text(prompt)
        title, content = self._parse_response(response)
        
        return {
            "title": title,
            "content": content
        }

    def _build_regeneration_prompt(self, 
                                  structured_data: Dict[str, Any], 
                                  style_prompt: Optional[str], 
                                  repost_context: Dict[str, Any], 
                                  blog: Dict[str, Any]) -> str:
        mode = repost_context.get("mode", "pure")
        metadata = structured_data.get("metadata", {})
        
        if mode == "pure":
            style_instruction = f"Maintain original style. Original tone: {metadata.get('tone', 'neutral')}"
        else:
            style_instruction = f"Apply style: {style_prompt}. Original tone: {metadata.get('tone', 'neutral')}"
        
        products_text = "\n".join(f"- {p.get('name', p)}" for p in repost_context.get("products", []))
        messages_text = "\n".join(f"- {msg}" for msg in repost_context.get("key_messages", []))
        
        structure_text = ""
        if structured_data.get("structure"):
            for i, section in enumerate(structured_data["structure"], 1):
                structure_text += f"{i}. {section.get('title', 'Section')}\n"
        
        return f"""Generate an article based on structured data.

Theme: {structured_data.get('theme', '')}
Structure:
{structure_text}
Products:
{products_text}
Key Messages:
{messages_text}
Style: {style_instruction}

Constraints:
- Use Markdown.
- No URLs.
- No meta-talk.

Output format:
タイトル: [Title]
本文:
[Content]
"""
    
    def _parse_response(self, response: str) -> tuple[str, str]:
        lines = response.strip().split('\n')
        title, content, in_content = "", "", False
        for line in lines:
            if line.startswith('タイトル:'):
                title = line.replace('タイトル:', '').strip()
            elif line.startswith('本文:'):
                in_content = True
            elif in_content:
                content += line + '\n'
        
        if not title:
            title = lines[0].strip() if lines else "Untitled"
            content = "\n".join(lines[1:]) if len(lines) > 1 else ""
        
        return title.strip(), content.strip()

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "StructuredArticleGeneratorTask"}
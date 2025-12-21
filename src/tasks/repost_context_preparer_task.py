"""
RepostContextPreparerTask - Prepares context for regeneration from structured data.
"""
import logging
from typing import Dict, Any, Optional

from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)

class RepostContextPreparerTask(BaseTaskModule):
    """
    Prepares context for article generation using structured data.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    @staticmethod
    def get_module_info():
        return {
            "name": "RepostContextPreparerTask",
            "description": "Prepares context for article regeneration from structured data."
        }

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        structured_data = inputs.get("structured_data")
        style_prompt = inputs.get("style_prompt")
        repost_mode = inputs.get("repost_mode")

        if not all([structured_data, repost_mode]):
            raise ValueError("Inputs 'structured_data' and 'repost_mode' are required.")
        
        logger.info(f"Preparing repost context for mode: {repost_mode}")
        
        article_concept = self._build_article_concept(structured_data, style_prompt, repost_mode)
        article_structure = self._build_article_structure(structured_data)
        repost_context = self._build_repost_context(structured_data, repost_mode)
        
        return {
            "article_concept": article_concept,
            "article_structure": article_structure,
            "repost_context": repost_context
        }

    def _build_article_concept(self, 
                              structured_data: Dict[str, Any], 
                              style_prompt: Optional[str], 
                              repost_mode: str) -> Dict[str, Any]:
        metadata = structured_data.get('metadata', {})
        return {
            "theme": structured_data["theme"],
            "target_keywords": structured_data.get("target_keywords", []),
            "target_audience": metadata.get("target_audience"),
            "is_repost": True,
            "original_tone": metadata.get("tone", "neutral"),
            "new_tone": style_prompt or metadata.get("tone", "neutral"),
            "repost_mode": repost_mode
        }

    def _build_article_structure(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        structure = structured_data.get("structure", [])
        return {
            "sections": structure,
            "word_count_target": sum(section.get("word_count", 0) for section in structure),
            "is_repost": True
        }

    def _build_repost_context(self, 
                             structured_data: Dict[str, Any], 
                             repost_mode: str) -> Dict[str, Any]:
        return {
            "mode": repost_mode,
            "products": structured_data.get("products", []),
            "key_messages": structured_data.get("key_messages", []),
            "content_elements": structured_data.get("content_elements", {}),
            "affiliate_strategy": structured_data.get("affiliate_strategy", {}),
            "original_metadata": structured_data.get("metadata", {})
        }
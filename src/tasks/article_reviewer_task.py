import logging
import re
from typing import Dict, Any, List
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class ArticleReviewer(BaseTaskModule):
    """
    Reviews article quality and provides feedback.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.gemini_service = GeminiService()
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            title = inputs.get('title', '')
            content = inputs.get('content', '')
            logger.info(f"Article review started: '{title[:50]}...'")
            
            review_prompt = f"Review this article: {title}\n\nContent:\n{content}"
            review_response = self.gemini_service.generate_text(review_prompt, task_priority="high")
            
            feedback, has_issues, suggestions = self._parse_review_response(review_response)
            return {
                "review_feedback": feedback,
                "has_issues": has_issues,
                "improvement_suggestions": suggestions,
                "revised_content": content
            }
        except Exception as e:
            logger.error(f"Review error: {e}")
            return {"review_feedback": str(e), "has_issues": False, "improvement_suggestions": [], "revised_content": content}

    def _parse_review_response(self, response: str) -> tuple:
        # Simple parser for recovery
        has_issues = "【指摘】" in response
        return response, has_issues, []

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "ArticleReviewer", "description": "Reviews article quality."}


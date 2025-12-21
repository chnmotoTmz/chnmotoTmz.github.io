__all__ = ["ArticleReviser"]
import logging
from typing import Dict, Any, List
from src.services.gemini_service import GeminiService
from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)

class ArticleReviser(BaseTaskModule):
    """Article Reviser Task"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.gemini_service = GeminiService()
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title = inputs.get('title', '')
        content = inputs.get('content', '')
        structured_sections = inputs.get('structured_sections')
        rule_based_only = self.config.get('rule_based_only', False)

        import re
        thumbnail_match = re.match(r"^\s*(!\[.*?\]\(http.*?\)\n*)", content)
        thumbnail_md = thumbnail_match.group(1) if thumbnail_match else ""

        if (structured_sections and isinstance(structured_sections, list)) or rule_based_only:
            if rule_based_only:
                logger.info("rule_based_only is enabled. Processing without LLM.")
            else:
                logger.info("Structured sections detected. Reconstructing Markdown.")
            
            content_no_thumb = content[len(thumbnail_md):] if thumbnail_md else content
            revised_content = self._structured_sections_to_markdown(structured_sections) if structured_sections else content_no_thumb
            revised_content = self._rule_based_link_injection(revised_content, inputs)
            final_content = thumbnail_md + revised_content
            
            return {
                "revised_title": title,
                "revised_content": final_content
            }

        logger.info(f"LLM-based revision started: '{title[:50]}'" )
        review_feedback = inputs.get('review_feedback', '')
        improvement_suggestions = inputs.get('improvement_suggestions', [])
        article_concept = inputs.get('article_concept', '')
        blog = inputs.get('blog', {})
        
        revision_prompt = self._build_revision_prompt(
            title, content, review_feedback, improvement_suggestions, 
            article_concept, blog
        )
        
        revision_response = self.gemini_service.generate_text(revision_prompt)
        revised_title, revised_content = self._parse_revision_response(
            revision_response, title, content
        )
        
        revised_content = self._rule_based_link_injection(revised_content, inputs)
        
        if thumbnail_md and not revised_content.strip().startswith("![ "):
            revised_content = thumbnail_md + revised_content.lstrip()

        return {
            "revised_title": revised_title,
            "revised_content": revised_content
        }

    def _rule_based_link_injection(self, content: str, inputs: Dict[str, Any]) -> str:
        product_links = {}
        web_summaries = inputs.get('web_summaries', [])
        for s in web_summaries:
            t, u = s.get('title', ''), s.get('url', '')
            if t and u: product_links[t] = u
        
        aff_strat = inputs.get('affiliate_strategy', {})
        target = aff_strat.get('target_product')
        url = aff_strat.get('amazon_url') or aff_strat.get('rakuten_url')
        if target and url: product_links[target] = url

        from src.utils.product_linker import insert_product_links
        return insert_product_links(content, product_links)

    def _structured_sections_to_markdown(self, sections: list) -> str:
        lines = []
        for section in sections:
            heading = section.get("heading") or section.get("title")
            content = section.get("content") or section.get("body")
            if heading: lines.append(f"## {heading}")
            if content: lines.append(content.strip())
            lines.append("")
        return "\n".join(lines).strip()
    
    def _build_revision_prompt(self, title: str, content: str, feedback: str,
                              suggestions: list, concept: str, blog: dict) -> str:
        s_text = "\n".join([f"- {s}" for s in suggestions]) if suggestions else "None"
        return f"Revise article.\n\nTitle: {title}\nContent:\n{content}\n\nFeedback: {feedback}\nSuggestions:\n{s_text}\n\nRules:\n1. Markdown format.\n2. No meta-talk.\n3. Use 【修正タイトル】 and 【修正本文】 sections."
    
    def _get_revised_content(self, prompt: str) -> str:
        """Geminiによる修正実施"""
        return self.gemini_service.generate_text(prompt)
    
    def _parse_revision_response(self, response: str, orig_title: str, 
                                 orig_content: str) -> tuple:
        """修正結果を解极E"""
        rev_title, rev_content = orig_title, orig_content
        
        if '【修正タイトル】' in response:
            start = response.find('【修正タイトル】') + len('【修正タイトル】')
            end = response.find('\n', start)
            rev_title = response[start:end if end != -1 else None].strip()
        
        if '【修正本文】' in response:
            start = response.find('【修正本文】') + len('【修正本文】')
            rev_content = response[start:].strip()
        else:
            rev_content = response.strip()
        
        return rev_title or orig_title, rev_content or orig_content
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "ArticleReviser",
            "description": "Revises article based on review or structured data.",
            "inputs": {
                "title": "str",
                "content": "str",
                "structured_sections": "List[Dict] (optional)"
            },
            "outputs": {
                "revised_title": "str",
                "revised_content": "str"
            }
        }
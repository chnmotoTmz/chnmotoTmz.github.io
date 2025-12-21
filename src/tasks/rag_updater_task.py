"""
RAGモデル自動更新タスク。

記事公開後にRAGモデルを自動的に更新し、
新しい記事を検索可能にします。
"""
import os
import logging
from typing import Dict, Any

from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)


class RagUpdaterTask(BaseTaskModule):
    """
    RAGモデルを更新するタスク。
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        RAGモデルを更新します。
        """
        enabled = self.config.get('enabled', True)
        env_enabled = os.getenv('ENABLE_AUTO_RAG_UPDATE', 'true').lower() == 'true'
        
        if not enabled or not env_enabled:
            logger.info("RAG auto-update is disabled. Skipping.")
            return {
                'success': True,
                'message': 'RAG update skipped'
            }

        try:
            from src.services.blog_rag_service import blog_rag_service

            blog = inputs.get('blog') or {}
            blog_id = blog.get('hatena_blog_id')
            api_key = blog.get('api_key') or blog.get('hatena_api_key')
            hatena_id = blog.get('hatena_id')

            logger.info(f"Starting RAG auto-update for blog: {blog_id or 'default'}")

            success, message = blog_rag_service.update_blog_rag_model(
                blog_id=blog_id,
                api_key=api_key,
                hatena_id=hatena_id,
            )
            
            return {
                'success': success,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"RAG update failed: {e}", exc_info=True)
            return {
                'success': False,
                'message': str(e)
            }

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "RagUpdater",
            "description": "Updates the RAG model."
        }
"""
StructuredDataLoaderTask - Loads structured data from the database/cache.
"""
import logging
import json
from typing import Dict, Any
from pathlib import Path
from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)

class StructuredDataLoaderTask(BaseTaskModule):
    """
    Loads structured post data.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    @staticmethod
    def get_module_info():
        return {
            "name": "StructuredDataLoaderTask",
            "description": "Loads structured post data from the database."
        }

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        structured_post_id = inputs.get("structured_post_id")
        if not structured_post_id:
            raise ValueError("Input 'structured_post_id' is required.")
            
        logger.info(f"Loading structured data for post_id: {structured_post_id}")
        cache_path = Path(f"data/cached_articles/{structured_post_id}.json")
        
        if not cache_path.exists():
            raise FileNotFoundError(f"Cached article not found: {cache_path}")
            
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                structured_data = json.load(f)
            return {"structured_data": structured_data}
        except Exception as e:
            logger.error(f"Error loading structured data: {e}")
            raise